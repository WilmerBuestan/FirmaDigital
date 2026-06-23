import { Navigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";

export default function RutaProtegida({ children }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
