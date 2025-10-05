import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../utils/api";

export default function ChatList() {
  const [sessions, setSessions] = useState([]);
  const navigate = useNavigate();

  const fetchSessions = async () => {
    const res = await API.get("/sessions");
    setSessions(res.data.sessions);
  };

  const createSession = async () => {
    const res = await API.post("/sessions", { session_name: "New Chat" });
    navigate(`/chat/${res.data.session_id}`);
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  return (
    <div>
      <h2>Your Chats</h2>
      <button onClick={createSession}>+ New Chat</button>
      <ul>
        {sessions.map((s) => (
          <li key={s.id} onClick={() => navigate(`/chat/${s.id}`)} style={{ cursor: "pointer" }}>
            {s.session_name} (updated {new Date(s.updated_at).toLocaleString()})
          </li>
        ))}
      </ul>
    </div>
  );
}
