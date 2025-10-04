// package main

// import (
// 	"context"
// 	"log"
// 	"net/http"
// 	"os"

// 	"github.com/gorilla/websocket"
// 	"google.golang.org/genai"
// )

// const modelName = "gemini-2.5-flash"

// var upgrader = websocket.Upgrader{
// 	CheckOrigin: func(r *http.Request) bool { return true },
// }

// func main() {
// 	apiKey := os.Getenv("GEMINI_API_KEY")
// 	if apiKey == "" {
// 		log.Fatal("GEMINI_API_KEY not set")
// 	}

// 	ctx := context.Background()
// 	client, err := genai.NewClient(ctx, &genai.ClientConfig{APIKey: apiKey})
// 	if err != nil {
// 		log.Fatal(err)
// 	}

// 	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
// 		conn, err := upgrader.Upgrade(w, r, nil)
// 		if err != nil {
// 			return
// 		}
// 		defer conn.Close()

// 		for {
// 			// Read message from client
// 			_, message, err := conn.ReadMessage()
// 			if err != nil {
// 				break
// 			}

// 			// Stream response from Gemini
// 			for result := range client.Models.GenerateContentStream(
// 				ctx,
// 				modelName,
// 				genai.Text(string(message)),
// 				nil,
// 			) {
// 				if len(result.Candidates) > 0 && len(result.Candidates[0].Content.Parts) > 0 {
// 					chunk := result.Candidates[0].Content.Parts[0].Text

// 					// Send each chunk as it arrives
// 					conn.WriteMessage(websocket.TextMessage, []byte(chunk))
// 				}
// 			}

// 			// Send END marker
// 			conn.WriteMessage(websocket.TextMessage, []byte("[[END]]"))
// 		}
// 	})

// 	log.Println("✅ Gemini WebSocket server started on ws://localhost:8765")
// 	log.Fatal(http.ListenAndServe(":8765", nil))
// }

package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

const modelName = "gemini-2.5-flash"

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

func main() {
	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		log.Fatal("GEMINI_API_KEY not set")
	}

	ctx := context.Background()
	client, err := genai.NewClient(ctx, &genai.ClientConfig{APIKey: apiKey})
	if err != nil {
		log.Fatal(err)
	}

	// WebSocket endpoint
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("WebSocket upgrade failed: %v", err)
			return
		}
		defer conn.Close()

		log.Println("Client connected")

		for {
			// Read message from client
			_, message, err := conn.ReadMessage()
			if err != nil {
				log.Printf("Read error: %v", err)
				break
			}

			log.Printf("Received: %s", string(message))

			// Stream response from Gemini
			results := client.Models.GenerateContentStream(
				ctx,
				modelName,
				genai.Text(string(message)),
				nil,
			)

			for result := range results {
				if len(result.Candidates) > 0 && len(result.Candidates[0].Content.Parts) > 0 {
					chunk := result.Candidates[0].Content.Parts[0].Text

					// Send each chunk as it arrives
					err = conn.WriteMessage(websocket.TextMessage, []byte(chunk))
					if err != nil {
						log.Printf("Write error: %v", err)
						break
					}
				}
			}

			// Send END marker
			conn.WriteMessage(websocket.TextMessage, []byte("[[END]]"))
			log.Println("Sent END marker")
		}

		log.Println("Client disconnected")
	})

	log.Println("✅ Gemini WebSocket server starting on :8765")
	log.Fatal(http.ListenAndServe(":8765", nil))
}
