import { useState } from "react";
import { login as loginApi } from "../api/auth";
import { AuthContext } from "./authContextDef";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));

  const isAuthenticated = Boolean(token);

  async function login(username, password) {
    const data = await loginApi(username, password);
    localStorage.setItem("token", data.access_token);
    setToken(data.access_token);
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
