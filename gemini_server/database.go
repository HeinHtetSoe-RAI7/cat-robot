package main

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/lib/pq"
)

var db *sql.DB

func InitDB() {
	dbURL := os.Getenv("DATABASE_URL")
	if dbURL == "" {
		log.Fatal("DATABASE_URL not set")
	}

	var err error
	db, err = sql.Open("postgres", dbURL)
	if err != nil {
		log.Fatalf("Failed to connect DB: %v", err)
	}

	if err = db.Ping(); err != nil {
		log.Fatalf("DB unreachable: %v", err)
	}

	log.Println("✅ Connected to PostgreSQL")
}

func CloseDB() {
	if db != nil {
		db.Close()
	}
}

func SaveMessage(userText, botReply string) error {
	_, err := db.Exec(`
		INSERT INTO messages (user_text, bot_reply, created_at)
		VALUES ($1, $2, NOW())
	`, userText, botReply)
	return err
}
