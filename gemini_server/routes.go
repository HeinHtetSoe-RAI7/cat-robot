package main

import (
	"encoding/json"
	"log"
	"net/http"
)

// ChatMessage represents a single chat stored in PostgreSQL
type ChatMessage struct {
	ID       int64  `json:"id"`
	UserText string `json:"user_text"`
	BotReply string `json:"bot_reply"`
	Created  string `json:"created_at"`
}

// RegisterRoutes registers REST endpoints
func RegisterRoutes() {
	// GET /chats - return last 100 messages
	http.HandleFunc("/chats", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		rows, err := db.Query("SELECT id, user_text, bot_reply, created_at FROM messages ORDER BY id DESC LIMIT 100")
		if err != nil {
			http.Error(w, "DB query error", http.StatusInternalServerError)
			log.Printf("DB query error: %v", err)
			return
		}
		defer rows.Close()

		var chats []ChatMessage
		for rows.Next() {
			var m ChatMessage
			if err := rows.Scan(&m.ID, &m.UserText, &m.BotReply, &m.Created); err != nil {
				log.Printf("Row scan error: %v", err)
				continue
			}
			chats = append(chats, m)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(chats)
	})
}
