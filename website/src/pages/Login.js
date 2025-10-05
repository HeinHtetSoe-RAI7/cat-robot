import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "../utils/api";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post("/api/login", { email, password });
      onLogin(res.data.token);
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("username", res.data.username);
      navigate("/chats");
    } catch (err) {
      setError("Invalid credentials");
      alert(err.response?.data?.error || "Login failed");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Sign In</h2>
      <input
        placeholder="Email"
        value={email}
        onChange={e => setEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={e => setPassword(e.target.value)}
        required
      />
      <button type="submit">Login</button>
      {error && <div style={{color: "red"}}>{error}</div>}
    </form>
  );
}
