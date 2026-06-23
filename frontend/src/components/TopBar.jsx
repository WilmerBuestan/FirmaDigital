import { NavLink } from "react-router-dom";
import { useAuth } from "../context/useAuth";

export default function TopBar() {
  const { logout } = useAuth();

  return (
    <header className="topbar">
      <div className="topbar-brand">
        <span className="auth-brand-icon" style={{ width: 30, height: 30 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
        FirmaSegura ESPE
      </div>

      <nav className="topbar-nav">
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Documentos
        </NavLink>
        <NavLink to="/perfil" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
          Mi perfil
        </NavLink>
      </nav>

      <button className="btn-secondary" onClick={logout}>Cerrar sesión</button>
    </header>
  );
}
