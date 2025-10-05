import React, { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import axios from "../utils/api";

export default function Chat({ token }) {
  const { id } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    axios
      .get("/api/chats", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => setMessages(res.data))
      .catch(() => setMessages([]));
  }, [token]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    try {
      const res = await axios.post(
        "/api/chat",
        { text: input },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMessages([...messages, ...res.data]); // expects array [{user, text}]
      setInput("");
    } catch (err) {
      alert("Failed to send message");
    }
  };

  return (
    <div>
      <h2>Chat with AI</h2>
      <div
        style={{
          height: "300px",
          overflowY: "auto",
          border: "1px solid #ccc",
          marginBottom: "1em",
        }}
      >
        {messages.map((msg, i) => (
          <div key={i}>
            <b>{msg.user}</b>: {msg.text}
          </div>
        ))}
      </div>
      <form onSubmit={sendMessage}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
