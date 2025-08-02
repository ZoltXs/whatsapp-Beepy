/**
 * WhatsApp Backend - Fixed Version
 * Corregidos los errores de sincronización y manejo de tokens
 */

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const bodyParser = require('body-parser');
const crypto = require('crypto');

const app = express();
const port = 3333;

// Estado global del cliente
let client = null;
let isAuthenticated = false;
let isReady = false;
let qrCode = '';
let connectionStatus = 'DISCONNECTED';
let initializationTimeout = null;
let isInitializing = false;

// Datos de aplicación
let contacts = [];
let chats = [];
let lastSync = null;

// Configuración de rutas de archivos
const PATHS = {
    auth: path.join(__dirname, '.whatsapp_session'),
    tokens: path.join(__dirname, '.whatsapp_tokens.json'),
    data: path.join(__dirname, 'whatsapp_data.json'),
    logs: path.join(__dirname, 'whatsapp.log')
};

// Logging mejorado
function log(message, level = 'INFO') {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] [${level}] ${message}`;
    console.log(logEntry);
    
    try {
        fs.appendFileSync(PATHS.logs, logEntry + '\n');
    } catch (err) {
        console.error('Error writing to log:', err.message);
    }
}

// Sistema de tokens corregido
class TokenManager {
    constructor() {
        this.authToken = null;
        this.refreshToken = null;
        this.tokenExpiry = null;
        this.loadTokens();
    }

    generateTokens() {
        const now = Date.now();
        this.authToken = crypto.randomBytes(32).toString('hex');
        this.refreshToken = crypto.randomBytes(32).toString('hex');
        this.tokenExpiry = now + (60 * 60 * 1000); // 1 hora
        
        log('New authentication tokens generated');
        this.saveTokens();
        return {
            authToken: this.authToken,
            refreshToken: this.refreshToken,
            expiresIn: 3600
        };
    }

    refreshTokens() {
        if (!this.refreshToken) {
            log('No refresh token available', 'WARN');
            return null;
        }

        const now = Date.now();
        this.authToken = crypto.randomBytes(32).toString('hex');
        this.tokenExpiry = now + (60 * 60 * 1000);
        
        log('Authentication tokens refreshed');
        this.saveTokens();
        return {
            authToken: this.authToken,
            refreshToken: this.refreshToken,
            expiresIn: 3600
        };
    }

    isTokenValid() {
        return this.authToken && this.tokenExpiry && Date.now() < this.tokenExpiry;
    }

    saveTokens() {
        try {
            const tokenData = {
                authToken: this.authToken,
                refreshToken: this.refreshToken,
                tokenExpiry: this.tokenExpiry,
                createdAt: Date.now(),
                sessionId: 'whatsapp-session-' + Date.now()
            };
            fs.writeFileSync(PATHS.tokens, JSON.stringify(tokenData, null, 2));
            log('Tokens saved successfully');
        } catch (error) {
            log(`Error saving tokens: ${error.message}`, 'ERROR');
        }
    }

    loadTokens() {
        try {
            if (fs.existsSync(PATHS.tokens)) {
                const tokenData = JSON.parse(fs.readFileSync(PATHS.tokens, 'utf8'));
                this.authToken = tokenData.authToken;
                this.refreshToken = tokenData.refreshToken;
                this.tokenExpiry = tokenData.tokenExpiry;
                
                if (this.isTokenValid()) {
                    log('Valid tokens loaded from storage');
                } else {
                    log('Loaded tokens are expired', 'WARN');
                    this.clearTokens();
                }
            }
        } catch (error) {
            log(`Error loading tokens: ${error.message}`, 'ERROR');
            this.clearTokens();
        }
    }

    clearTokens() {
        this.authToken = null;
        this.refreshToken = null;
        this.tokenExpiry = null;
        
        try {
            if (fs.existsSync(PATHS.tokens)) {
                fs.unlinkSync(PATHS.tokens);
            }
        } catch (error) {
            log(`Error clearing tokens: ${error.message}`, 'ERROR');
        }
    }
}

const tokenManager = new TokenManager();

// Sistema de sesiones
class SessionManager {
    constructor() {
        this.ensureSessionDirectory();
    }

    ensureSessionDirectory() {
        try {
            if (!fs.existsSync(PATHS.auth)) {
                fs.mkdirSync(PATHS.auth, { recursive: true, mode: 0o755 });
                log('Session directory created');
            }
        } catch (error) {
            log(`Error setting up session directory: ${error.message}`, 'ERROR');
        }
    }

    hasValidSession() {
        try {
            const sessionPath = path.join(PATHS.auth, 'session-whatsapp');
            return fs.existsSync(sessionPath) && fs.readdirSync(sessionPath).length > 0;
        } catch (error) {
            return false;
        }
    }

    clearSession() {
        try {
            if (fs.existsSync(PATHS.auth)) {
                fs.rmSync(PATHS.auth, { recursive: true, force: true });
                log('Session cleared');
            }
            this.ensureSessionDirectory();
        } catch (error) {
            log(`Error clearing session: ${error.message}`, 'ERROR');
        }
    }
}

const sessionManager = new SessionManager();

// Función para limpiar procesos de Chromium
function cleanupChromiumProcesses() {
    try {
        const { execSync } = require('child_process');
        
        try {
            execSync('pkill -f chromium-browser', { stdio: 'ignore' });
            log('Cleaned up existing Chromium processes');
        } catch (e) {
            // No hay procesos para limpiar
        }
        
        const tempDirs = [
            '/tmp/.org.chromium.Chromium.*',
            '/dev/shm/.org.chromium.Chromium.*'
        ];
        
        tempDirs.forEach(pattern => {
            try {
                execSync(`rm -rf ${pattern}`, { stdio: 'ignore' });
            } catch (e) {
                // Ignorar errores de limpieza
            }
        });
        
    } catch (error) {
        log(`Warning during cleanup: ${error.message}`, 'WARN');
    }
}

// Función para cargar datos
function loadData() {
    try {
        if (fs.existsSync(PATHS.data)) {
            const data = JSON.parse(fs.readFileSync(PATHS.data, 'utf8'));
            contacts = data.contacts || [];
            chats = data.chats || [];
            lastSync = data.lastSync || null;
            log(`Data loaded: ${contacts.length} contacts, ${chats.length} chats`);
        }
    } catch (error) {
        log(`Error loading data: ${error.message}`, 'ERROR');
    }
}

// Función para guardar datos
function saveData() {
    try {
        const data = {
            contacts,
            chats,
            lastSync,
            version: '1.2.1-fixed',
            timestamp: Date.now()
        };
        fs.writeFileSync(PATHS.data, JSON.stringify(data, null, 2));
        log('Data saved successfully');
    } catch (error) {
        log(`Error saving data: ${error.message}`, 'ERROR');
    }
}

// Filtrado de contactos mejorado
function filterValidContacts(rawContacts) {
    if (!Array.isArray(rawContacts)) {
        log('Invalid contacts array received', 'WARN');
        return [];
    }
    
    return rawContacts.filter(contact => {
        try {
            if (contact.isGroup) return false;
            if (!contact.isMyContact) return false;
            
            const name = contact.name || contact.pushname || '';
            if (name.length < 2) return false;
            
            // Debe contener al menos una letra
            if (!/[a-zA-ZÀ-ÿ\u0100-\u017F\u0180-\u024F\u1E00-\u1EFF]/.test(name)) return false;
            
            // Rechazar si es solo un número de teléfono
            if (/^[\+\-\s\(\)\d]+$/.test(name.trim())) return false;
            
            return true;
        } catch (error) {
            log(`Error filtering contact: ${error.message}`, 'WARN');
            return false;
        }
    });
}

// Sincronización de contactos corregida
async function syncContacts() {
    if (!client || !isReady) {
        log('Cannot sync contacts - client not ready', 'WARN');
        return contacts;
    }

    try {
        log('Starting contact synchronization...');
        const rawContacts = await client.getContacts();
        
        if (!rawContacts) {
            log('No contacts received from client', 'WARN');
            return contacts;
        }
        
        const validContacts = filterValidContacts(rawContacts);
        
        // Eliminar duplicados por número
        const contactMap = new Map();
        validContacts.forEach(contact => {
            try {
                const key = contact.number || contact.id._serialized;
                if (!contactMap.has(key)) {
                    contactMap.set(key, {
                        id: contact.id._serialized,
                        name: contact.name || contact.pushname || '',
                        number: contact.number,
                        isGroup: false,
                        isMyContact: true
                    });
                }
            } catch (error) {
                log(`Error processing contact: ${error.message}`, 'WARN');
            }
        });

        contacts = Array.from(contactMap.values()).sort((a, b) => a.name.localeCompare(b.name));
        
        log(`Contact sync completed: ${rawContacts.length} -> ${contacts.length} valid contacts`);
        saveData();
        return contacts;
    } catch (error) {
        log(`Error syncing contacts: ${error.message}`, 'ERROR');
        return contacts;
    }
}

// Sincronización de chats corregida
async function syncChats() {
    if (!client || !isReady) {
        log('Cannot sync chats - client not ready', 'WARN');
        return chats;
    }

    try {
        log('Starting chat synchronization...');
        const rawChats = await client.getChats();
        
        if (!rawChats) {
            log('No chats received from client', 'WARN');
            return chats;
        }
        
        chats = [];

        for (const chat of rawChats) {
            try {
                const lastMessage = chat.lastMessage;
                chats.push({
                    id: chat.id._serialized,
                    name: chat.name,
                    isGroup: chat.isGroup,
                    unreadCount: chat.unreadCount,
                    lastMessage: lastMessage ? {
                        body: lastMessage.body,
                        timestamp: lastMessage.timestamp,
                        from: lastMessage.from
                    } : null
                });
            } catch (chatError) {
                log(`Error processing chat ${chat.id._serialized}: ${chatError.message}`, 'WARN');
            }
        }

        lastSync = new Date().toISOString();
        log(`Chat sync completed: ${chats.length} chats`);
        saveData();
        return chats;
    } catch (error) {
        log(`Error syncing chats: ${error.message}`, 'ERROR');
        return chats;
    }
}

// Inicialización del cliente WhatsApp corregida
async function initializeWhatsAppClient() {
    if (isInitializing) {
        log('Initialization already in progress, skipping', 'WARN');
        return;
    }
    
    try {
        isInitializing = true;
        log('Initializing WhatsApp client with improved error handling...');
        connectionStatus = 'CONNECTING';

        // Limpiar timeout anterior
        if (initializationTimeout) {
            clearTimeout(initializationTimeout);
            initializationTimeout = null;
        }

        // Limpiar procesos de Chromium antes de iniciar
        cleanupChromiumProcesses();
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Destruir cliente anterior si existe
        if (client) {
            try {
                await client.destroy();
                log('Previous client destroyed');
                await new Promise(resolve => setTimeout(resolve, 2000));
            } catch (destroyError) {
                log(`Warning destroying previous client: ${destroyError.message}`, 'WARN');
            }
        }

        // Crear nuevo cliente con configuración mejorada
        client = new Client({
            authStrategy: new LocalAuth({
                clientId: 'whatsapp',
                dataPath: PATHS.auth
            }),
            puppeteer: {
                executablePath: '/usr/bin/chromium-browser',
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-features=TranslateUI,VizDisplayCompositor',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--memory-pressure-off',
                    '--max_old_space_size=512',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--disable-background-networking',
                    '--disable-sync',
                    '--disable-default-apps',
                    '--disable-client-side-phishing-detection'
                ],
                timeout: 120000,
                handleSIGINT: false,
                handleSIGTERM: false,
                handleSIGHUP: false
            }
        });

        // Timeout para la inicialización (5 minutos)
        initializationTimeout = setTimeout(() => {
            log('Initialization timeout - retrying...', 'WARN');
            isInitializing = false;
            initializeWhatsAppClient();
        }, 300000);

        // Event handlers
        client.on('qr', (qr) => {
            log('QR Code generated - ready for authentication');
            qrCode = qr;
            connectionStatus = 'QR_READY';
            
            if (initializationTimeout) {
                clearTimeout(initializationTimeout);
                initializationTimeout = null;
            }
        });

        client.on('authenticated', () => {
            log('WhatsApp client authenticated successfully!');
            isAuthenticated = true;
            connectionStatus = 'AUTHENTICATED';
            tokenManager.generateTokens();
        });

        client.on('ready', async () => {
            log('WhatsApp client is ready and connected!');
            isReady = true;
            connectionStatus = 'READY';
            qrCode = '';
            isInitializing = false;

            if (initializationTimeout) {
                clearTimeout(initializationTimeout);
                initializationTimeout = null;
            }

            // Sincronización inicial con delay
            setTimeout(async () => {
                try {
                    await syncContacts();
                    await syncChats();
                    log('Initial synchronization completed');
                } catch (syncError) {
                    log(`Initial sync error: ${syncError.message}`, 'ERROR');
                }
            }, 5000);
        });

        client.on('auth_failure', (message) => {
            log(`Authentication failed: ${message}`, 'ERROR');
            isAuthenticated = false;
            connectionStatus = 'AUTH_FAILED';
            isInitializing = false;
            tokenManager.clearTokens();
            
            if (initializationTimeout) {
                clearTimeout(initializationTimeout);
                initializationTimeout = null;
            }
            
            setTimeout(() => {
                sessionManager.clearSession();
                cleanupChromiumProcesses();
                setTimeout(() => initializeWhatsAppClient(), 5000);
            }, 10000);
        });

        client.on('disconnected', (reason) => {
            log(`WhatsApp disconnected: ${reason}`, 'WARN');
            isReady = false;
            isAuthenticated = false;
            connectionStatus = 'DISCONNECTED';
            isInitializing = false;

            if (initializationTimeout) {
                clearTimeout(initializationTimeout);
                initializationTimeout = null;
            }

            if (reason !== 'LOGOUT') {
                setTimeout(() => {
                    log('Attempting to reconnect...');
                    cleanupChromiumProcesses();
                    setTimeout(() => initializeWhatsAppClient(), 5000);
                }, 15000);
            }
        });

        client.on('change_state', (state) => {
            log(`Connection state changed: ${state}`);
        });

        client.on('error', (error) => {
            log(`Client error: ${error.message}`, 'ERROR');
        });

        // Inicializar cliente
        await client.initialize();
        
    } catch (error) {
        log(`Error initializing WhatsApp client: ${error.message}`, 'ERROR');
        connectionStatus = 'ERROR';
        isInitializing = false;
        
        if (initializationTimeout) {
            clearTimeout(initializationTimeout);
            initializationTimeout = null;
        }
        
        cleanupChromiumProcesses();
        setTimeout(() => {
            initializeWhatsAppClient();
        }, 30000);
    }
}

// Express middleware
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(__dirname));

// Rutas principales
app.get('/', (req, res) => {
    res.redirect('/connect');
});

app.get('/connect', (req, res) => {
    res.sendFile(path.join(__dirname, 'connect.html'));
});

app.get('/connect/whatsapp', (req, res) => {
    res.sendFile(path.join(__dirname, 'qr_connect.html'));
});

app.get('/connect/spotify', (req, res) => {
    res.redirect('http://' + req.get('host').split(':')[0] + ':3001');
});

app.get('/connect/mail', (req, res) => {
    res.sendFile(path.join(__dirname, 'mail_config.html'));
});

app.get('/test_form.html', (req, res) => {
    res.sendFile(path.join(__dirname, 'test_form.html'));
});

// API Status
app.get('/status', (req, res) => {
    const tokenValid = tokenManager.isTokenValid();
    const hasSession = sessionManager.hasValidSession();
    
    res.json({
        ready: isReady,
        authenticated: isAuthenticated,
        status: connectionStatus,
        hasQR: qrCode !== '',
        qr: qrCode,
        contactsCount: contacts.length,
        chatsCount: chats.length,
        lastSync: lastSync,
        session: {
            exists: hasSession,
            valid: hasSession && isAuthenticated
        },
        tokens: {
            valid: tokenValid,
            expiresAt: tokenManager.tokenExpiry,
            hasRefreshToken: !!tokenManager.refreshToken
        },
        version: '1.2.1-fixed'
    });
});

// API Contactos
app.get('/contacts', async (req, res) => {
    try {
        if (isReady) {
            const freshContacts = await syncContacts();
            res.json({ success: true, contacts: freshContacts });
        } else {
            res.json({ success: true, contacts: contacts, cached: true });
        }
    } catch (error) {
        log(`Error getting contacts: ${error.message}`, 'ERROR');
        res.status(500).json({ success: false, error: error.message });
    }
});

// API Chats
app.get('/chats', async (req, res) => {
    try {
        const { groups = 'true' } = req.query;
        const includeGroups = groups === 'true';
        
        let chatList = chats;
        if (isReady) {
            chatList = await syncChats();
        }
        
        const filteredChats = includeGroups ? chatList : chatList.filter(chat => !chat.isGroup);
        res.json({ success: true, chats: filteredChats });
    } catch (error) {
        log(`Error getting chats: ${error.message}`, 'ERROR');
        res.status(500).json({ success: false, error: error.message });
    }
});

// API Enviar mensaje
app.post('/send-message', async (req, res) => {
    const { to, message } = req.body;
    
    if (!isReady) {
        return res.status(400).json({ success: false, error: 'WhatsApp not ready' });
    }
    
    if (!tokenManager.isTokenValid() && isAuthenticated) {
        tokenManager.refreshTokens();
    }
    
    try {
        log(`Sending message to ${to}: ${message.substring(0, 50)}...`);
        const result = await client.sendMessage(to, message);
        
        res.json({ 
            success: true, 
            messageId: result.id._serialized,
            timestamp: Date.now()
        });
    } catch (error) {
        log(`Error sending message: ${error.message}`, 'ERROR');
        res.status(500).json({ success: false, error: error.message });
    }
});

// API Sincronización completa - CORREGIDA
app.post('/sync/all', async (req, res) => {
    try {
        if (!isReady) {
            return res.status(400).json({ 
                success: false, 
                error: 'WhatsApp not ready',
                status: connectionStatus 
            });
        }
        
        log('Starting full synchronization...');
        
        // Sincronizar de forma secuencial para evitar problemas
        const freshContacts = await syncContacts();
        const freshChats = await syncChats();
        
        res.json({
            success: true,
            contacts: freshContacts.length,
            chats: freshChats.length,
            lastSync: lastSync,
            timestamp: Date.now()
        });
    } catch (error) {
        log(`Sync error: ${error.message}`, 'ERROR');
        res.status(500).json({ 
            success: false, 
            error: error.message,
            stack: error.stack 
        });
    }
});

// API Reset completo
app.post('/account/reset', async (req, res) => {
    try {
        log('Resetting WhatsApp account...');
        
        // Limpiar timeout
        if (initializationTimeout) {
            clearTimeout(initializationTimeout);
            initializationTimeout = null;
        }
        
        isInitializing = false;
        
        if (client) {
            await client.destroy();
        }
        
        // Limpiar todo
        sessionManager.clearSession();
        tokenManager.clearTokens();
        cleanupChromiumProcesses();
        
        // Reset estado
        isReady = false;
        isAuthenticated = false;
        connectionStatus = 'DISCONNECTED';
        qrCode = '';
        contacts = [];
        chats = [];
        lastSync = null;
        
        saveData();
        
        // Reinicializar
        setTimeout(() => initializeWhatsAppClient(), 5000);
        
        res.json({ success: true, message: 'Account reset successfully' });
    } catch (error) {
        log(`Reset error: ${error.message}`, 'ERROR');
        res.status(500).json({ success: false, error: error.message });
    }
});

// API Refresh manual de tokens
app.post('/tokens/refresh', (req, res) => {
    try {
        if (!isAuthenticated) {
            return res.status(400).json({ success: false, error: 'Not authenticated' });
        }
        
        const newTokens = tokenManager.refreshTokens();
        if (newTokens) {
            res.json({ success: true, tokens: newTokens });
        } else {
            res.status(400).json({ success: false, error: 'Failed to refresh tokens' });
        }
    } catch (error) {
        log(`Token refresh error: ${error.message}`, 'ERROR');
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get chat by contact ID
app.get('/chat/:contactId', async (req, res) => {
    const { contactId } = req.params;
    
    if (!isReady) {
        return res.status(400).json({ success: false, error: 'WhatsApp not ready' });
    }
    
    try {
        const chat = await client.getChatById(contactId);
        res.json({ success: true, chat });
    } catch (error) {
        res.status(404).json({ success: false, error: 'Chat not found' });
    }
});

// Send a new message to a specific chat
app.post('/chat/:chatId/send', async (req, res) => {
    const { chatId } = req.params;
    const { message } = req.body;
    
    if (!isReady) {
        return res.status(400).json({ success: false, error: 'WhatsApp not ready' });
    }
    
    try {
        const result = await client.sendMessage(chatId, message);
        res.json({ success: true, messageId: result.id._serialized });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Manejo de cierre con limpieza
process.on('SIGINT', async () => {
    log('Shutting down gracefully...');
    
    if (initializationTimeout) {
        clearTimeout(initializationTimeout);
    }
    
    if (client) {
        await client.destroy();
    }
    
    cleanupChromiumProcesses();
    process.exit(0);
});

process.on('SIGTERM', async () => {
    log('Received SIGTERM - shutting down...');
    
    if (initializationTimeout) {
        clearTimeout(initializationTimeout);
    }
    
    if (client) {
        await client.destroy();
    }
    
    cleanupChromiumProcesses();
    process.exit(0);
});

// Iniciar servidor
app.listen(port, '0.0.0.0', () => {
    log(`WhatsApp Backend (Fixed Version) running on http://localhost:${port}`);
    log('Features: Fixed sync errors + Better error handling + Token management');
    log(`Connect URL: http://localhost:${port}/connect`);
    
    loadData();
    initializeWhatsAppClient();
    
    // Refresh automático de tokens cada hora
    setInterval(() => {
        if (isAuthenticated && tokenManager.isTokenValid()) {
            tokenManager.refreshTokens();
            log('Automatic token refresh completed');
        }
    }, 60 * 60 * 1000);
});

// ==========================================
// ENDPOINT PARA MENSAJES REALES DE WHATSAPP
// ==========================================

// Obtener mensajes reales de un chat específico
app.get('/chat/:chatId/messages', async (req, res) => {
    const { chatId } = req.params;
    const { limit = 30 } = req.query;
    
    if (!isReady) {
        return res.status(400).json({ 
            success: false, 
            error: 'WhatsApp not ready',
            status: connectionStatus
        });
    }
    
    try {
        log(`Fetching real messages for chat: ${chatId}`);
        
        // Obtener el chat
        const chat = await client.getChatById(chatId);
        
        // Obtener mensajes reales
        const messages = await chat.fetchMessages({ limit: parseInt(limit) });
        
        // Formatear mensajes con toda la información necesaria
        const formattedMessages = messages.map(msg => ({
            id: msg.id._serialized,
            body: msg.body || '',
            fromMe: msg.fromMe,
            timestamp: msg.timestamp,
            from: msg.from,
            to: msg.to,
            type: msg.type,
            author: msg.author || msg.from,
            isForwarded: msg.isForwarded || false,
            hasMedia: msg.hasMedia || false,
            mediaType: msg.type !== 'chat' ? msg.type : null
        }));
        
        // Información del chat
        const chatInfo = {
            id: chat.id._serialized,
            name: chat.name,
            isGroup: chat.isGroup,
            unreadCount: chat.unreadCount || 0,
            lastSeen: chat.lastSeen || null
        };
        
        log(`Successfully fetched ${formattedMessages.length} real messages for ${chat.name}`);
        
        res.json({
            success: true,
            chat: chatInfo,
            messages: formattedMessages,
            messageCount: formattedMessages.length,
            timestamp: Date.now()
        });
        
    } catch (error) {
        log(`Error fetching messages for ${chatId}: ${error.message}`, 'ERROR');
        res.status(404).json({ 
            success: false, 
            error: 'Chat not found or messages unavailable',
            details: error.message,
            chatId: chatId
        });
    }
});

// Endpoint modificado para obtener chat con mensajes integrados
app.get('/chat/:contactId', async (req, res) => {
    const { contactId } = req.params;
    const { includeMessages = 'true', limit = 20 } = req.query;
    
    if (!isReady) {
        return res.status(400).json({ 
            success: false, 
            error: 'WhatsApp not ready',
            status: connectionStatus
        });
    }
    
    try {
        log(`Fetching chat info for: ${contactId}`);
        const chat = await client.getChatById(contactId);
        
        const chatData = {
            id: chat.id._serialized,
            name: chat.name,
            isGroup: chat.isGroup,
            unreadCount: chat.unreadCount || 0
        };
        
        let messages = [];
        
        // Si se solicitan mensajes, obtenerlos
        if (includeMessages === 'true') {
            try {
                const fetchedMessages = await chat.fetchMessages({ limit: parseInt(limit) });
                messages = fetchedMessages.map(msg => ({
                    id: msg.id._serialized,
                    body: msg.body || '',
                    fromMe: msg.fromMe,
                    timestamp: msg.timestamp,
                    from: msg.from,
                    type: msg.type,
                    author: msg.author || msg.from
                }));
                log(`Fetched ${messages.length} messages for ${chat.name}`);
            } catch (msgError) {
                log(`Could not fetch messages: ${msgError.message}`, 'WARN');
                messages = [];
            }
        }
        
        res.json({
            success: true,
            chat: chatData,
            messages: messages,
            messageCount: messages.length,
            hasMessages: messages.length > 0
        });
        
    } catch (error) {
        log(`Error fetching chat ${contactId}: ${error.message}`, 'ERROR');
        res.status(404).json({ 
            success: false, 
            error: 'Chat not found',
            details: error.message 
        });
    }
});

