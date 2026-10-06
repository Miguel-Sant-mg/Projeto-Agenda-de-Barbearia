import unittest
import socket
from app import app, obter_ip_local

class TestServerSecurityAndConfig(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_security_headers_present(self):
        """Verifica se todos os cabeçalhos de segurança HTTP estão presentes na resposta."""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(resp.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(resp.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(resp.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    def test_admin_routes_protected_against_unauthenticated_access(self):
        """Garante que todas as rotas administrativas redirecionam para o login."""
        rotas_protegidas = [
            "/admin",
            "/admin/dashboard",
            "/admin/agenda",
            "/admin/faturamento",
            "/admin/clientes",
            "/admin/config",
            "/agendamentos",
            "/api/admin/faturamento-dados",
            "/api/admin/dashboard-stats",
            "/api/admin/agendamentos-recentes"
        ]

        for rota in rotas_protegidas:
            resp = self.client.get(rota, follow_redirects=False)
            self.assertEqual(
                resp.status_code, 302, 
                f"Rota {rota} deve redirecionar (302) usuário não autenticado para /login"
            )
            self.assertIn("/login", resp.headers.get("Location", ""))

    def test_local_ip_discovery(self):
        """Valida que a função de descoberta de IP local retorna um IP IPv4 válido."""
        ip = obter_ip_local()
        self.assertIsInstance(ip, str)
        partes = ip.split(".")
        self.assertEqual(len(partes), 4, f"IP retornado '{ip}' deve ser um endereço IPv4 válido")
        for p in partes:
            self.assertTrue(p.isdigit())
            self.assertTrue(0 <= int(p) <= 255)

    def test_session_cookie_settings(self):
        """Valida se os cookies de sessão estão configurados com HttpOnly e SameSite seguro."""
        self.assertTrue(app.config.get("SESSION_COOKIE_HTTPONLY"))
        self.assertEqual(app.config.get("SESSION_COOKIE_SAMESITE"), "Lax")

if __name__ == "__main__":
    unittest.main()
