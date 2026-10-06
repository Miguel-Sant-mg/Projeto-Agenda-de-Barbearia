# 💈 Barbearia Arte de Favela - Web Server & Sistema de Agendamento

Sistema completo de agendamento online e painel administrativo para barbearias, configurado como servidor web local seguro para acesso via computadores e celulares conectados na mesma rede Wi-Fi.

---

## 🚀 Como Executar o Servidor Web

### 1. Instalar Dependências

Certifique-se de ter o **Python 3.10+** instalado no computador servidor. No terminal da pasta do projeto, execute:

```bash
python -m pip install -r requirements.txt
```

---

### 2. Configurar Variáveis de Ambiente (`.env`)

Copie o arquivo de exemplo `.env.example` para `.env`:

```bash
copy .env.example .env
```

*(No PowerShell: `cp .env.example .env`)*

Principais opções configuráveis no `.env`:
* **`HOST=0.0.0.0`**: Permite que o servidor escute conexões locais e de outros dispositivos na rede Wi-Fi.
* **`PORT=5000`**: Porta onde o servidor web irá rodar (altere se desejar outra porta).
* **`FLASK_ENV=development`**: `development` (desenvolvimento) ou `production` (produção com servidor WSGI Waitress).
* **`FLASK_SECRET_KEY`**: Chave para criptografia de sessões de login e cookies.
* **`SERVER_ENGINE=flask`**: `flask` (servidor de desenvolvimento) ou `waitress` (servidor de produção).

---

### 3. Iniciar o Servidor

Você pode iniciar o servidor de 3 formas simples:

#### Opção A: Pelo Terminal (Prompt de Comando ou PowerShell)
```bash
python app.py
```

#### Opção B: Clicando duas vezes no arquivo Windows Batch
Dê um duplo clique no arquivo:
```text
iniciar_servidor.bat
```

#### Opção C: Executando o script PowerShell
```powershell
.\iniciar_servidor.ps1
```

Ao iniciar, o terminal exibirá automaticamente os links de acesso local e de rede.

---

## 💻 4. Acesso pelo Computador (Servidor)

No próprio computador onde o servidor está rodando, abra o navegador e acesse:

* **Site do Cliente:** [http://localhost:5000](http://localhost:5000) ou [http://127.0.0.1:5000](http://127.0.0.1:5000)
* **Painel Administrativo:** [http://localhost:5000/login](http://localhost:5000/login)

> **Credenciais padrão do Barbeiro:**
> * **Usuário:** `admin`
> * **Senha:** `admin123`

---

## 📱 5. Acesso pelo Celular (Mesma Rede Wi-Fi)

Para que clientes ou barbeiros acessem pelo celular:

1. Conecte o celular na **mesma rede Wi-Fi** onde o computador servidor está conectado.
2. Descubra o IP local do computador servidor no Windows:
   * Abra o terminal (Prompt de Comando ou PowerShell).
   * Digite `ipconfig` e pressione Enter.
   * Procure pelo **Adaptador de Rede Sem Fio Wi-Fi** (ou Ethernet) e localize a linha:
     ```text
     Endereço IPv4. . . . . . . . . . . . . : 192.168.1.105 (exemplo)
     ```
3. No navegador do celular (Chrome, Safari, etc.), digite:
   ```text
   http://192.168.1.105:5000
   ```
   *(Substitua `192.168.1.105` pelo IP IPv4 real exibido no seu terminal)*

---

## 🛡️ 6. Configuração do Windows Defender Firewall

Caso o Windows Defender Firewall solicite permissão ou impeça o acesso de outros dispositivos na rede Wi-Fi, configure uma regra **estritamente para Rede Privada** (nunca desative o Firewall nem libere para Redes Públicas):

### Opção via PowerShell (Como Administrador):
```powershell
New-NetFirewallRule -DisplayName "Barbearia Arte de Favela (Porta 5000)" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow -Profile Private
```

### Opção via Interface Gráfica do Windows:
1. Abra o **Painel de Controle** → **Sistema e Segurança** → **Windows Defender Firewall**.
2. Clique em **Configurações avançadas** no menu à esquerda.
3. Clique em **Regras de Entrada** → **Nova Regra...**.
4. Selecione **Porta** → Avançar.
5. Selecione **TCP** e em Portas locais específicas digite: `5000`.
6. Selecione **Permitir a conexão** → Avançar.
7. **IMPORTANTE:** Marque apenas a caixa **Privada** (desmarque *Domínio* e *Pública*).
8. Dê o nome: `Barbearia Arte de Favela` e clique em Concluir.

---

## 🔒 7. Medidas de Segurança Implementadas

1. **Autenticação em Nível de Backend:**
   * Todas as páginas administrativas (`/admin`, `/admin/dashboard`, `/admin/agenda`, `/admin/faturamento`, `/admin/clientes`, `/admin/config`) e APIs internas estão protegidas pelo decorator `@login_required`.
   * Tentativas de acesso não autenticado são interceptadas e redirecionadas para o login.

2. **Privacidade e Proteção de Dados de Clientes:**
   * A rota de listagem bruta de agendamentos (`/agendamentos`) é restrita a administradores autenticados.
   * Clientes comuns não conseguem visualizar dados pessoais ou telefones de outros clientes.

3. **Criptografia de Senhas:**
   * Senhas são armazenadas utilizando hashes criptográficos modernos (`pbkdf2:sha256` / `scrypt`), sem senhas em texto puro.

4. **Proteção contra SQL Injection:**
   * 100% das consultas ao banco de dados SQLite utilizam consultas parametrizadas (`?`).

5. **Cookies de Sessão Seguros:**
   * `SESSION_COOKIE_HTTPONLY = True` (impede acesso a cookies via scripts JS/XSS).
   * `SESSION_COOKIE_SAMESITE = 'Lax'` (proteção contra ataques CSRF).

6. **Cabeçalhos de Segurança HTTP:**
   * `X-Content-Type-Options: nosniff`
   * `X-Frame-Options: SAMEORIGIN` (proteção contra Clickjacking)
   * `X-XSS-Protection: 1; mode=block`
   * `Referrer-Policy: strict-origin-when-cross-origin`

7. **Validação Estrita de Agendamento e Horário de Almoço:**
   * Validação de nomes, formato de telefone com DDD, datas válidas e prevenção atômica de horários duplicados.
   * Bloqueio do horário de almoço das 13:00 às 14:00 (13:00 e 13:30) com feedback visual e rejeição no backend.

8. **Isolamento de Credenciais:**
   * Suporte a `.env` com modelo `.env.example`.
   * Arquivo `.gitignore` configurado para impedir o versionamento de `.env`, bancos de dados locais e caches.

---

## 📱 8. Responsividade em Múltiplos Dispositivos

A interface foi otimizada para os seguintes formatos de tela:
* **Smartphones pequenos (360px - 390px):** iPhone SE, Galaxy A/S, telas compactas.
* **Smartphones modernos (390px - 480px):** iPhone 13/14/15/16, Galaxy S23/S24, Xiaomi.
* **Tablets (768px - 1024px):** iPad, Galaxy Tab.
* **Notebooks e Desktops (1366px - 1920px+):** Telas HD, Full HD e monitores widescreen.

---

## 🌐 9. Preparação para Publicação na Internet (Futuro)

Para transformar este servidor local em um serviço público com domínio na internet:

1. **Servidor em Nuvem:**
   * Hospedar em VPS Linux (Ubuntu 22.04/24.04) na AWS, DigitalOcean, Hetzner ou Linode.
2. **Proxy Reverso (Nginx):**
   * Configurar Nginx para receber requisições nas portas 80/443 e repassar para o WSGI server (Gunicorn / Waitress) via socket ou porta interna (`127.0.0.1:5000`).
3. **Certificado SSL/TLS (HTTPS):**
   * Instalar Certbot / Let's Encrypt para emissão de certificado SSL gratuito e renovação automática:
     ```bash
     sudo certbot --nginx -d seusite.com.br -d www.seusite.com.br
     ```
   * Ativar `FLASK_COOKIE_SECURE=true` no `.env`.
4. **Gerenciador de Processos:**
   * Configurar `systemd` para manter o serviço sempre em execução e reiniciar automaticamente em caso de reboot do servidor.
5. **Rotina de Backup:**
   * Configurar cron job para backup diário criptografado do banco de dados `agenda.db` para armazenamento em nuvem (S3/Google Drive).

---

## 📋 Resumo dos Comandos

| Etapa | Comando |
| :--- | :--- |
| **Instalar dependências** | `python -m pip install -r requirements.txt` |
| **Criar arquivo de configuração** | `copy .env.example .env` |
| **Iniciar Servidor** | `python app.py` ou duplo clique em `iniciar_servidor.bat` |
| **Descobrir IP da Rede** | `ipconfig` *(no Windows)* |
| **Acesso Local (PC)** | `http://localhost:5000` |
| **Acesso Celular (Wi-Fi)** | `http://<SEU-IP-LOCAL>:5000` |
