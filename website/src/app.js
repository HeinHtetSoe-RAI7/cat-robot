import React, { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "../pages/Login";
import Register from "../pages/Register";
import Chat from "../pages/Chat";

function App() {
  const [token, setToken] = useState(localStorage.getItem("token"));

  const handleLogin = (newToken) => {
    setToken(newToken);
    localStorage.setItem("token", newToken);
  };

  const handleLogout = () => {
    setToken(null);
    localStorage.removeItem("token");
  };

  return (
    <BrowserRouter>
      <div>
        {token && <button onClick={handleLogout}>Logout</button>}
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/chat"
            element={token ? <Chat token={token} /> : <Navigate to="/login" />}
          />
          <Route path="*" element={<Navigate to={token ? "/chat" : "/login"} />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;

app.listen(5000, () => console.log("Server running on port 5000"));