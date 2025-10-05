CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_text TEXT NOT NULL,
    bot_reply TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
