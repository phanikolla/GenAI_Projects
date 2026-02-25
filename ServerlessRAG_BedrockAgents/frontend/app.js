/**
 * ServerlessRAG — Frontend Application
 * Auth via Cognito REST API, data via API Gateway
 * No backend server required — fully static / S3-hosted
 */

// ── Configuration (edit these for your deployment) ──
const CONFIG = {
  COGNITO_REGION: 'us-east-1',
  COGNITO_CLIENT_ID: '661t0g6shec37d2l3sd8c6v8ps',
  API_GATEWAY_URL: 'https://4qgg2qvin4.execute-api.us-east-1.amazonaws.com/prod'
};

const COGNITO_URL = `https://cognito-idp.${CONFIG.COGNITO_REGION}.amazonaws.com/`;

const app = {
  // ── State ─────────────────────────────
  accessToken: null,
  idToken: null,
  refreshToken: null,
  userEmail: null,
  userName: null,
  sessionId: null,
  documents: [],
  pendingDeleteId: null,
  pendingDeleteName: null,

  // ── Initialization ────────────────────
  init() {
    const saved = localStorage.getItem('rag_session');
    if (saved) {
      try {
        const session = JSON.parse(saved);
        this.accessToken = session.accessToken;
        this.idToken = session.idToken;
        this.refreshToken = session.refreshToken;
        this.userEmail = session.email;
        this.userName = session.name || session.email?.split('@')[0];
        this.showApp();
        this.loadDocuments();
      } catch {
        localStorage.removeItem('rag_session');
      }
    }

    // Drag & drop handlers
    const zone = document.getElementById('upload-zone');
    if (zone) {
      zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover'); });
      zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
      zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith('.pdf')) {
          this.uploadFile(file);
        } else {
          this.showAlert('upload', 'error', 'Only PDF files are supported');
        }
      });
    }
  },

  // ═══════════════════════════════════════
  // Auth — Direct Cognito REST API calls
  // ═══════════════════════════════════════
  showLogin() {
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('signup-form').classList.add('hidden');
    this.clearAlerts();
  },

  showSignup() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('signup-form').classList.remove('hidden');
    this.clearAlerts();
  },

  async cognitoRequest(action, payload) {
    const res = await fetch(COGNITO_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': `AWSCognitoIdentityProviderService.${action}`
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.message || data.__type || 'Cognito request failed');
    }
    return data;
  },

  async handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const btn = document.getElementById('login-btn');

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div>';

    try {
      const result = await this.cognitoRequest('InitiateAuth', {
        AuthFlow: 'USER_PASSWORD_AUTH',
        ClientId: CONFIG.COGNITO_CLIENT_ID,
        AuthParameters: {
          USERNAME: email,
          PASSWORD: password
        }
      });

      const auth = result.AuthenticationResult;
      this.accessToken = auth.AccessToken;
      this.idToken = auth.IdToken;
      this.refreshToken = auth.RefreshToken;
      this.userEmail = email;
      this.userName = email.split('@')[0];

      localStorage.setItem('rag_session', JSON.stringify({
        accessToken: this.accessToken,
        idToken: this.idToken,
        refreshToken: this.refreshToken,
        email: this.userEmail,
        name: this.userName
      }));

      this.showApp();
      this.loadDocuments();
    } catch (err) {
      this.showAlert('login', 'error', err.message || 'Invalid credentials');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-text">Sign In</span>';
    }
  },

  async handleSignup(e) {
    e.preventDefault();
    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const password = document.getElementById('signup-password').value;
    const btn = document.getElementById('signup-btn');

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div>';

    try {
      await this.cognitoRequest('SignUp', {
        ClientId: CONFIG.COGNITO_CLIENT_ID,
        Username: email,
        Password: password,
        UserAttributes: [
          { Name: 'email', Value: email },
          { Name: 'name', Value: name }
        ]
      });

      this.showAlert('signup', 'success', 'Account created! Check your email for a verification code.');
      this.userEmail = email;
      document.getElementById('confirm-form').classList.add('show');
    } catch (err) {
      this.showAlert('signup', 'error', err.message || 'Signup failed');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-text">Create Account</span>';
    }
  },

  async handleConfirm(e) {
    e.preventDefault();
    const code = document.getElementById('confirm-code').value.trim();

    try {
      await this.cognitoRequest('ConfirmSignUp', {
        ClientId: CONFIG.COGNITO_CLIENT_ID,
        Username: this.userEmail,
        ConfirmationCode: code
      });

      this.showAlert('signup', 'success', 'Account verified! You can now sign in.');
      document.getElementById('confirm-form').classList.remove('show');
      setTimeout(() => this.showLogin(), 1500);
    } catch (err) {
      this.showAlert('signup', 'error', err.message || 'Verification failed');
    }
  },

  logout() {
    this.accessToken = null;
    this.idToken = null;
    this.refreshToken = null;
    this.userEmail = null;
    this.userName = null;
    this.sessionId = null;
    this.documents = [];
    localStorage.removeItem('rag_session');

    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-screen').classList.add('hidden');
    this.clearAlerts();
    this.showLogin();
  },

  showApp() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-screen').classList.remove('hidden');

    const avatar = this.userName ? this.userName.charAt(0).toUpperCase() : '?';
    document.getElementById('user-avatar').textContent = avatar;
    document.getElementById('user-name').textContent = this.userName || 'User';
    document.getElementById('user-email').textContent = this.userEmail || '';
  },

  // ═══════════════════════════════════════
  // Documents — via API Gateway
  // ═══════════════════════════════════════
  async loadDocuments() {
    try {
      const res = await this.apiGw('/documents', 'GET');
      this.documents = res.documents || [];
      this.renderDocuments();
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  },

  renderDocuments() {
    const list = document.getElementById('doc-list');
    const empty = document.getElementById('doc-empty');
    const count = document.getElementById('doc-count');

    count.textContent = this.documents.length;

    if (this.documents.length === 0) {
      empty.style.display = 'block';
      list.querySelectorAll('.doc-item').forEach(el => el.remove());
      return;
    }

    empty.style.display = 'none';

    const fragment = document.createDocumentFragment();
    this.documents.forEach(doc => {
      const item = document.createElement('div');
      item.className = 'doc-item';
      item.innerHTML = `
        <div class="doc-icon">📄</div>
        <div class="doc-info">
          <div class="doc-name" title="${this.escapeHtml(doc.filename || doc.key || 'Unknown')}">${this.escapeHtml(doc.filename || doc.key || 'Unknown')}</div>
          <div class="doc-meta">${doc.size ? this.formatSize(doc.size) : ''} ${doc.status ? '· ' + doc.status : ''}</div>
        </div>
        <button class="doc-delete" onclick="app.requestDelete('${this.escapeHtml(doc.document_id || doc.key)}','${this.escapeHtml(doc.filename || doc.key || 'Unknown')}')" title="Delete">✕</button>
      `;
      fragment.appendChild(item);
    });

    list.querySelectorAll('.doc-item').forEach(el => el.remove());
    list.appendChild(fragment);
  },

  handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) this.uploadFile(file);
    e.target.value = '';
  },

  async uploadFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are supported');
      return;
    }

    const progress = document.getElementById('upload-progress');
    const fill = document.getElementById('progress-fill');
    const text = document.getElementById('progress-text');

    progress.classList.add('show');
    fill.style.width = '30%';
    text.textContent = `Uploading ${file.name}...`;

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Upload via API Gateway: documents POST
      const res = await fetch(`${CONFIG.API_GATEWAY_URL}/documents`, {
        method: 'POST',
        headers: { 'Authorization': this.idToken },
        body: formData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || err.error || `Upload failed (${res.status})`);
      }

      fill.style.width = '100%';
      text.textContent = 'Indexing started! ✓';

      await this.loadDocuments();

      setTimeout(() => {
        progress.classList.remove('show');
        fill.style.width = '0%';
      }, 2000);

    } catch (err) {
      text.textContent = `Error: ${err.message}`;
      fill.style.width = '0%';
      setTimeout(() => progress.classList.remove('show'), 3000);
    }
  },

  requestDelete(docId, docName) {
    this.pendingDeleteId = docId;
    this.pendingDeleteName = docName;
    document.getElementById('delete-doc-name').textContent = docName;
    document.getElementById('delete-modal').classList.remove('hidden');
  },

  cancelDelete() {
    this.pendingDeleteId = null;
    document.getElementById('delete-modal').classList.add('hidden');
  },

  async confirmDelete() {
    if (!this.pendingDeleteId) return;
    const docId = this.pendingDeleteId;
    this.cancelDelete();

    try {
      await this.apiGw(`/documents/${encodeURIComponent(docId)}`, 'DELETE');
      await this.loadDocuments();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  },

  // ═══════════════════════════════════════
  // Chat — via API Gateway /query
  // ═══════════════════════════════════════
  newSession() {
    this.sessionId = null;
    const messages = document.getElementById('chat-messages');
    messages.querySelectorAll('.message').forEach(el => el.remove());
    document.getElementById('chat-welcome').classList.remove('hidden');
    document.getElementById('chat-input').value = '';
    document.getElementById('chat-input').focus();
  },

  useSuggestion(text) {
    document.getElementById('chat-input').value = text;
    document.getElementById('chat-input').focus();
    this.autoResize(document.getElementById('chat-input'));
    this.sendMessage();
  },

  handleInputKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      this.sendMessage();
    }
  },

  autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
  },

  async sendMessage() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;

    document.getElementById('chat-welcome').classList.add('hidden');
    this.addMessage('user', question);
    input.value = '';
    input.style.height = 'auto';

    const typing = this.addTypingIndicator();
    document.getElementById('send-btn').disabled = true;

    try {
      const res = await this.apiGw('/query', 'POST', {
        question,
        session_id: this.sessionId
      });

      typing.remove();
      if (res.session_id) this.sessionId = res.session_id;
      this.addMessage('assistant', res.answer, res.sources);

    } catch (err) {
      typing.remove();
      this.addMessage('assistant', `Sorry, I encountered an error: ${err.message}. Please try again.`);
    } finally {
      document.getElementById('send-btn').disabled = false;
      document.getElementById('chat-input').focus();
    }
  },

  addMessage(role, text, sources) {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const avatarContent = role === 'assistant' ? '🧠' : (this.userName?.charAt(0).toUpperCase() || '?');
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    let sourcesHtml = '';
    if (sources && sources.length > 0) {
      const tags = sources.map(s => {
        const name = typeof s === 'string' ? s : (s.filename || s.document_id || 'Doc');
        return `<span class="source-tag">📄 ${this.escapeHtml(name)}</span>`;
      }).join('');
      sourcesHtml = `<div class="message-sources">${tags}</div>`;
    }

    div.innerHTML = `
      <div class="message-avatar">${avatarContent}</div>
      <div class="message-content">
        <div class="message-bubble">${this.formatText(text)}</div>
        ${sourcesHtml}
        <div class="message-meta">${time}</div>
      </div>
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
  },

  addTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.innerHTML = `
      <div class="message-avatar">🧠</div>
      <div class="message-content">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
      </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div;
  },

  // ═══════════════════════════════════════
  // API Gateway Helper
  // ═══════════════════════════════════════
  async apiGw(endpoint, method = 'GET', body = null) {
    const headers = {};
    // API Gateway Cognito authorizer expects raw ID token (no "Bearer" prefix)
    if (this.idToken) {
      headers['Authorization'] = this.idToken;
    }
    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
    }

    const opts = { method, headers };
    if (body) {
      opts.body = body instanceof FormData ? body : JSON.stringify(body);
    }

    const res = await fetch(`${CONFIG.API_GATEWAY_URL}${endpoint}`, opts);

    if (res.status === 401) {
      // Try token refresh
      if (this.refreshToken) {
        const refreshed = await this.tryRefresh();
        if (refreshed) {
          headers['Authorization'] = this.idToken;
          const retry = await fetch(`${CONFIG.API_GATEWAY_URL}${endpoint}`, { method, headers, body: opts.body });
          if (!retry.ok) {
            const err = await retry.json().catch(() => ({}));
            throw new Error(err.detail || err.error || `Request failed (${retry.status})`);
          }
          return retry.json();
        }
      }
      this.logout();
      throw new Error('Session expired. Please sign in again.');
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || err.error || `Request failed (${res.status})`);
    }

    return res.json();
  },

  async tryRefresh() {
    try {
      const result = await this.cognitoRequest('InitiateAuth', {
        AuthFlow: 'REFRESH_TOKEN_AUTH',
        ClientId: CONFIG.COGNITO_CLIENT_ID,
        AuthParameters: {
          REFRESH_TOKEN: this.refreshToken
        }
      });

      const auth = result.AuthenticationResult;
      this.accessToken = auth.AccessToken;
      this.idToken = auth.IdToken;
      // Refresh token stays the same

      const saved = JSON.parse(localStorage.getItem('rag_session') || '{}');
      saved.accessToken = this.accessToken;
      saved.idToken = this.idToken;
      localStorage.setItem('rag_session', JSON.stringify(saved));
      return true;
    } catch {
      return false;
    }
  },

  // ═══════════════════════════════════════
  // Utilities
  // ═══════════════════════════════════════
  showAlert(screen, type, message) {
    const el = document.getElementById(`${screen}-alert`);
    if (!el) return;
    el.className = `alert alert-${type} show`;
    el.textContent = message;
  },

  clearAlerts() {
    document.querySelectorAll('.alert').forEach(el => {
      el.classList.remove('show');
    });
  },

  escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  },

  formatText(text) {
    return this.escapeHtml(text)
      .replace(/\n/g, '<br/>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.*?)`/g, '<code style="background:rgba(124,92,252,0.15);padding:2px 6px;border-radius:4px;font-size:13px;">$1</code>');
  },

  formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  }
};

// Boot on DOM ready
document.addEventListener('DOMContentLoaded', () => app.init());
