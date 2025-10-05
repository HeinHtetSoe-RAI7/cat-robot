package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

const modelName = "gemini-2.5-flash-lite"

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

func main() {
	// Initialize DB
	InitDB()
	defer CloseDB()

	// Register REST endpoints
	RegisterRoutes()

	apiKey := os.Getenv("GEMINI_API_KEY")
	if apiKey == "" {
		log.Fatal("GEMINI_API_KEY not set")
	}

	ctx := context.Background()
	client, err := genai.NewClient(ctx, &genai.ClientConfig{APIKey: apiKey})
	if err != nil {
		log.Fatal(err)
	}

	systemInstruction := "You are a student (a kid) practicing English with your teacher. " +
		"You will receive sentences from your teacher. " +
		"Your role is to behave like a curious kid, respond naturally, and keep a childlike tone."

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Printf("WebSocket upgrade failed: %v", err)
			return
		}
		defer conn.Close()

		log.Println("Client connected")

		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				log.Printf("Read error: %v", err)
				break
			}

			userText := string(message)
			log.Printf("Received: %s", userText)

			contents := []*genai.Content{
				genai.NewContentFromText(userText, genai.RoleUser),
			}

			cfg := &genai.GenerateContentConfig{
				SystemInstruction: genai.NewContentFromText(systemInstruction, genai.Role("system")),
			}

			results := client.Models.GenerateContentStream(ctx, modelName, contents, cfg)

			var fullReply string
			for result := range results {
				if len(result.Candidates) > 0 && len(result.Candidates[0].Content.Parts) > 0 {
					chunk := result.Candidates[0].Content.Parts[0].Text
					fullReply += chunk

					if err := conn.WriteMessage(websocket.TextMessage, []byte(chunk)); err != nil {
						log.Printf("Write error: %v", err)
						break
					}
				}
			}

			conn.WriteMessage(websocket.TextMessage, []byte("[[END]]"))
			log.Println("Sent END marker")

			// Save chat to DB
			if err := SaveMessage(userText, fullReply); err != nil {
				log.Printf("DB save error: %v", err)
			}
		}

		log.Println("Client disconnected")
	})

	log.Println("✅ Gemini WebSocket server running on :8765")
	log.Fatal(http.ListenAndServe(":8765", nil))
}
