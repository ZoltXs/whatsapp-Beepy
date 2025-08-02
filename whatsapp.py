import os
"""
WhatsApp Module for LightBerry OS
ENHANCED VERSION - Smart Sync, larger conversation text, complete functionality
"""

import pygame
import requests
import time
import threading

# Constants (inline to avoid config dependency)
BACKGROUND_COLOR = (23, 23, 23)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (34, 139, 34)
SELECTED_COLOR = (45, 45, 55)
ERROR_COLOR = (139, 34, 34)
SUCCESS_COLOR = (34, 139, 34)
HIGHLIGHT_COLOR = (100, 200, 100)
WARNING_COLOR = (255, 255, 0)

class MockOS:
    """Mock OS instance to replace lightberry OS dependencies"""
    def __init__(self):
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        self.font_s = pygame.font.Font(None, 20)
        self.font_m = pygame.font.Font(None, 24)
        self.font_l = pygame.font.Font(None, 28)
        self.font_tiny = pygame.font.Font(None, 16)


class WhatsApp:
    def __init__(self, os_instance=None):
        if os_instance is None:
            self.os = MockOS()
        else:
            self.os = os_instance
        self.backend_url = "http://localhost:3333"
        
        # Module state - added smart_sync mode
        self.mode = "splash"  # welcome -> loading -> main_menu -> chat_list/new_chat/smart_sync -> contact_search -> chat_view -> compose
        self.connection_stable = False
        self.data_loaded = False
        
        # Chat data
        self.chats = []
        self.contacts = []  # Store all contacts for search
        self.current_chat = None
        self.current_messages = []
        
        # Navigation state
        self.selected_chat_index = 0
        self.selected_menu_index = 0
        self.selected_contact_index = 0
        self.message_input = ""
        self.search_input = ""
        self.compose_mode = False
        self.message_scroll = 0
        self.input_lines = []
        self.search_results = []
        
        # Smart Sync status
        self.sync_status = ""
        self.sync_progress = 0
        self.sync_complete = False
        
        # Status
        self.status_message = "Welcome to WhatsApp"
        self.error_message = ""
        self.loading_dots = 0
        
        # Screen dimensions
        self.screen_width = 400
        self.screen_height = 240
        # Splash screen
        self.splash_start_time = time.time()
        self.splash_duration = 3.0  # Duración del splash en segundos
        self.splash_image = None
        self.background_image = None
        
        # Load splash image
        self.load_splash_image()
        self.load_background_image()

        
        # Start loading after welcome screen
        self.schedule_loading()
        # Start real-time updates
        self.start_realtime_updates()

    def load_splash_image(self):
        """Load the WhatsApp splash image"""
        try:
            image_path = "/home/pi/lightberry/modules/images/whatsapp.jpg"
            print(f"🖼️ Intentando cargar imagen WhatsApp desde: {image_path}")
            
            if os.path.exists(image_path) and os.access(image_path, os.R_OK):
                import pygame
                # Asegurar que pygame esté inicializado
                if not pygame.get_init():
                    pygame.init()
                
                self.splash_image = pygame.image.load(image_path).convert()
                self.splash_image = pygame.transform.scale(self.splash_image, (400, 240))
                print("✅ Imagen de splash de WhatsApp cargada correctamente")
            else:
                print(f"⚠️ Sin permisos de lectura para {image_path}")
                self.splash_image = None
        except Exception as e:
            print(f"❌ Error cargando imagen de splash WhatsApp: {e}")
            self.splash_image = None

    

    def load_background_image(self):
        """Load the chat background image"""
        try:
            image_path = "/home/pi/whatsapp/images/whatsbacground.jpg"
            if os.path.exists(image_path):
                import pygame
                if not pygame.get_init():
                    pygame.init()
                self.background_image = pygame.image.load(image_path).convert()
                self.background_image = pygame.transform.scale(self.background_image, (self.screen_width, self.screen_height))
                print("✅ Background image loaded successfully.")
            else:
                print(f"❌ Background image not found: {image_path}")
                self.background_image = None
        except Exception as e:
            print(f"❌ Error loading background image: {e}")
            self.background_image = None

    def start_new_chat_with_contact(self, contact):
        """Start new chat with selected contact - check for existing conversation first"""
        if not contact:
            self.error_message = "No contact selected"
            return
        
        contact_id = contact.get("id", "")
        
        # First, check if we already have a chat with this contact
        existing_chat = None
        for chat in self.chats:
            if chat.get("id") == contact_id:
                existing_chat = chat
                break
        
        if existing_chat:
            # Load existing conversation
            print(f"DEBUG: Found existing chat with {contact.get('name')}")
            self.load_chat_messages(existing_chat)
        else:
            # Create a new chat object for the contact
            new_chat = {
                "id": contact_id,
                "name": contact.get("name", "Unknown"),
                "isGroup": False
            }
            print(f"DEBUG: Creating new chat with {contact.get('name')}")
            self.load_chat_messages(new_chat)
    def schedule_loading(self):
        """Schedule data loading after welcome screen"""
    def draw_background_safely(self, screen):
        """Safely draw background image with error handling"""
        try:
            if self.background_image:
                screen.blit(self.background_image, (0, 0))
                overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                screen.blit(overlay, (0, 0))
            else:
                screen.fill(BACKGROUND_COLOR)
        except Exception as e:
            print(f"Background error: {e}")
            screen.fill(BACKGROUND_COLOR)
        def delayed_start():
            time.sleep(2)  # Show welcome for 2 seconds minimum
            if self.mode == "welcome":
                self.mode = "loading"
                self.status_message = "Loading data"
                self.manual_smart_sync()
        
        threading.Thread(target=delayed_start, daemon=True).start()
    def start_smart_sync(self):
        """Start smart sync - load all data including contacts"""
        def sync():
            try:
                import socket
                socket.setdefaulttimeout(3)  # Timeout corto
                self.status_message = "Connecting to WhatsApp..."
                
                # Test backend connection con timeout
                response = requests.get(f"{self.backend_url}/status", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("ready", False):
                        self.connection_stable = True
                        self.status_message = "Loading chats..."
                        
                        # Load chats
                        self.load_chats_sync()
                        
                        # Load all contacts for search
                        self.status_message = "Loading contacts..."
                        self.load_contacts_sync()
                        
                        # Mark as loaded and go to main menu
                        self.data_loaded = True
                        self.mode = "main_menu"
                        self.status_message = f"Ready - {len(self.chats)} chats, {len(self.contacts)} contacts"
                        self.error_message = ""
                        return
                        
                # Backend not ready - fallback
                self.error_message = "Backend not ready"
                time.sleep(2)  # Brief pause
                self.mode = "main_menu"
                self.status_message = "WhatsApp (offline mode)"
                        
            except Exception as e:
                print(f"WhatsApp sync error: {e}")
                # Connection failed - go to main menu anyway
                self.error_message = "Connection failed - offline mode"
                time.sleep(2)  # Brief pause to show error
                self.mode = "main_menu"
                self.status_message = "WhatsApp (offline mode)"
                self.data_loaded = True  # Mark as \"loaded\" to prevent retry
        
        threading.Thread(target=sync, daemon=True).start()
    
    def reset_account_data(self):
        """Delete all synchronized data from backend server"""
        try:
            response = requests.delete(f"{self.backend_url}/api/reset-account", timeout=10)
            if response.status_code == 200:
                self.mode = "reset_account_info"
                self.status_message = "Account data deleted successfully"
            else:
                self.error_message = f"Reset failed: {response.status_code}"
                self.mode = "main_menu"
        except requests.exceptions.RequestException as e:
            self.error_message = f"Reset failed: Connection error"
            self.mode = "main_menu"
    


    def manual_smart_sync(self):
        """Manual Smart Sync - comprehensive data synchronization"""
        def sync():
            try:
                self.sync_status = "Starting Smart Sync..."
                self.sync_progress = 0
                self.sync_complete = False
                self.error_message = ""
                
                # Step 1: Check backend status
                self.sync_status = "Checking connection..."
                self.sync_progress = 10
                response = requests.get(f"{self.backend_url}/status", timeout=10)
                
                if response.status_code != 200:
                    self.error_message = "Backend not accessible"
                    self.sync_complete = True
                    return
                
                data = response.json()
                self.sync_status = f"Backend status: {data.get('status', 'Unknown')}"
                self.sync_progress = 20
                
                if not data.get("ready", False):
                    if data.get("hasQR", False):
                        self.error_message = "Scan QR code first - visit http://localhost:3333"
                    else:
                        self.error_message = "WhatsApp not ready - initializing..."
                    self.sync_complete = True
                    return
                
                # Step 2: Load contacts
                self.sync_status = "Loading contacts..."
                self.sync_progress = 30
                contacts_response = requests.get(f"{self.backend_url}/contacts", timeout=15)
                
                if contacts_response.status_code == 200:
                    contacts_data = contacts_response.json()
                    if contacts_data.get("success", False):
                        self.contacts = contacts_data.get("contacts", [])
                        self.sync_status = f"Loaded {len(self.contacts)} contacts"
                        self.sync_progress = 50
                    else:
                        self.sync_status = "No contacts available"
                        self.contacts = []
                else:
                    self.sync_status = "Failed to load contacts"
                    self.contacts = []
                
                # Step 3: Load chats
                self.sync_status = "Loading chats..."
                self.sync_progress = 60
                chats_response = requests.get(f"{self.backend_url}/chats", timeout=15)
                
                if chats_response.status_code == 200:
                    chats_data = chats_response.json()
                    if chats_data.get("success", False):
                        self.chats = chats_data.get("chats", [])
                        self.sync_status = f"Loaded {len(self.chats)} chats"
                        self.sync_progress = 80
                    else:
                        self.sync_status = "No chats available"
                        self.chats = []
                else:
                    self.sync_status = "Failed to load chats"
                    self.chats = []
                
                # Step 4: Complete
                self.sync_progress = 100
                self.sync_status = f"Sync complete! {len(self.contacts)} contacts, {len(self.chats)} chats"
                self.data_loaded = True
                self.connection_stable = True
                self.sync_complete = True
                
                # Auto-return to main menu after success
                time.sleep(2)
                if self.mode == "smart_sync":
                    self.mode = "main_menu"
                    self.status_message = self.sync_status
                
            except requests.exceptions.ConnectionError:
                self.error_message = "Backend connection failed - is server running?"
                self.sync_complete = True
            except requests.exceptions.Timeout:
                self.error_message = "Sync timeout - server too slow"
                self.sync_complete = True
            except Exception as e:
                self.error_message = f"Sync error: {str(e)[:40]}"
                self.sync_complete = True
        
        threading.Thread(target=sync, daemon=True).start()

    def start_realtime_updates(self):
        """Start real-time chat updates that preserve conversation history"""
        def update_loop():
            while True:
                time.sleep(1)  # Check every 1 second for real-time updates
                if self.connection_stable and self.current_chat and self.mode == "chat_view":
                    self.check_for_new_messages()
                    
        threading.Thread(target=update_loop, daemon=True).start()
    
    def check_for_new_messages(self):
        """Check for new messages without replacing the conversation"""
        def check():
            try:
                if not self.current_chat or not self.current_chat.get("id"):
                    return
                
                chat_id = self.current_chat.get("id", "").replace("@", "%40")
                response = requests.get(f"{self.backend_url}/chat/{chat_id}", timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        chat_data = data.get("chat", {})
                        last_message = chat_data.get("lastMessage")
                        
                        if last_message and last_message.get("body"):
                            # Check if this message is already in our conversation
                            message_id = last_message.get("id", {})
                            if isinstance(message_id, dict):
                                message_id = message_id.get("_serialized", str(time.time()))
                            else:
                                message_id = str(message_id)
                            
                            # Check if we already have this message
                            already_exists = False
                            for existing_msg in self.current_messages:
                                existing_id = existing_msg.get("id", "")
                                if str(existing_id) == str(message_id):
                                    already_exists = True
                                    break
                            
                            # If it's a new message, add it to the conversation
                            if not already_exists:
                                filtered_text = self.filter_text_only(last_message.get("body"))
                                if filtered_text and filtered_text not in ["[Non-text content]", "[Filtered content]"]:
                                    new_message = {
                                        "id": message_id,
                                        "body": last_message.get("body"),
                                        "fromMe": last_message.get("fromMe", False),
                                        "timestamp": last_message.get("timestamp", int(time.time())),
                                        "type": "chat"
                                    }
                                    
                                    # Add to the end of conversation
                                    self.current_messages.append(new_message)
                                    
                                    # Keep a reasonable limit of messages
                                    if len(self.current_messages) > 100:
                                        self.current_messages = self.current_messages[-100:]
                                    
                                    # Auto-scroll to show new message
                                    if self.mode == "chat_view":
                                        available_height = 170 - 50
                                        line_height = 18
                                        max_visible_lines = available_height // line_height
                                        if len(self.current_messages) > max_visible_lines:
                                            self.message_scroll = len(self.current_messages) - max_visible_lines
                                    
                                    print(f"DEBUG: New message added to conversation")
                    
            except Exception as e:
                print(f"DEBUG: Error checking for new messages: {e}")
        
        threading.Thread(target=check, daemon=True).start()
    def load_chats_sync(self):
        """Load chat list synchronously"""
        try:
            response = requests.get(f"{self.backend_url}/chats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                raw_chats = data.get("chats", [])
                
                # Filter and validate chats
                self.chats = []
                for chat in raw_chats:
                    if chat.get("name") and chat.get("id"):
                        self.chats.append(chat)
                
                print(f"DEBUG: Loaded {len(self.chats)} valid chats")
                
            else:
                raise Exception(f"Failed to load chats: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"DEBUG: Chat loading error: {e}")
            raise e

    def load_contacts_sync(self):
        """Load all contacts synchronously - NO LIMITS"""
        try:
            response = requests.get(f"{self.backend_url}/contacts", timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                raw_contacts = data.get("contacts", [])
                
                # Filter and validate contacts - keep ALL valid ones
                self.contacts = []
                for contact in raw_contacts:
                    name = contact.get("name", "").strip()
                    contact_id = contact.get("id", "")
                    
                    # Only filter out completely invalid entries
                    if name and name != "Unknown" and name != "" and contact_id:
                        self.contacts.append({
                            "id": contact_id,
                            "name": name,
                            "phone": contact.get("phone", ""),
                            "pushname": contact.get("pushname", name)
                        })
                
                # Sort contacts alphabetically for better search experience
                self.contacts.sort(key=lambda x: x.get("name", "").lower())
                
                print(f"DEBUG: Loaded {len(self.contacts)} valid contacts")
                
            else:
                raise Exception(f"Failed to load contacts: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"DEBUG: Contact loading error: {e}")
            raise e
    
    def search_contacts(self, query):
        """Search contacts by name - returns all matches"""
        if not query.strip():
            self.search_results = []
            return
        
        query_lower = query.lower().strip()
        self.search_results = []
        
        for contact in self.contacts:
            name = contact.get("name", "").lower()
            if query_lower in name:
                self.search_results.append(contact)
        
        # Reset selection when search results change
        self.selected_contact_index = 0
        
        print(f"DEBUG: Search '{query}' found {len(self.search_results)} results")
    
    def filter_text_only(self, text):
        """Filter text to remove emojis, emoticonos, multimedia references and keep only readable text"""
        if not text:
            return ""
        
        try:
            # Convert to string and handle None
            text = str(text) if text is not None else ""
            
            # Remove common multimedia indicators
            multimedia_patterns = [
                "image omitted", "video omitted", "audio omitted", "document omitted",
                "sticker omitted", "gif omitted", "location omitted", "contact omitted",
                "[IMAGE]", "[VIDEO]", "[AUDIO]", "[DOCUMENT]", "[STICKER]", "[GIF]",
                "[LOCATION]", "[CONTACT]", "📷", "🎥", "🎵", "📄", "📍"
            ]
            
            text_lower = text.lower()
            for pattern in multimedia_patterns:
                if pattern.lower() in text_lower:
                    return "[Media content]"
            
            # Remove URLs
            import re
            text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[Link]', text)
            text = re.sub(r'www\.(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[Link]', text)
            
            # Filter out problematic Unicode characters (emojis, symbols)
            filtered_chars = []
            for char in text:
                try:
                    # Keep only basic Latin, Latin extended, numbers, punctuation and common symbols
                    if ord(char) <= 0xFFFF:  # Basic Multilingual Plane
                        if (ord(char) < 32 and char not in '\n\r\t') or \
                           (0x2600 <= ord(char) <= 0x26FF) or \
                           (0x2700 <= ord(char) <= 0x27BF) or \
                           (0x1F600 <= ord(char) <= 0x1F64F) or \
                           (0x1F300 <= ord(char) <= 0x1F5FF) or \
                           (0x1F680 <= ord(char) <= 0x1F6FF) or \
                           (0x1F1E6 <= ord(char) <= 0x1F1FF):
                            # Skip emojis and special symbols
                            continue
                        else:
                            filtered_chars.append(char)
                    # Skip characters above BMP (like some emojis)
                except ValueError:
                    continue
            
            filtered_text = ''.join(filtered_chars).strip()
            
            # If the text is empty after filtering, provide a placeholder
            if not filtered_text:
                return "[Non-text content]"
            
            # Limit length to prevent display issues
            if len(filtered_text) > 200:
                filtered_text = filtered_text[:197] + "..."
            
            return filtered_text
            
        except Exception as e:
            print(f"Text filtering error: {e}")
            return "[Filtered content]"
    def safe_render_text(self, text, font, color):
        """Safely render text avoiding Unicode errors"""
        try:
            if not text or text.strip() == "":
                return font.render("[Empty]", True, color)
            
            # Additional safety filter
            safe_text = self.filter_text_only(text)
            
            # Try to render the text
            return font.render(safe_text, True, color)
            
        except Exception as e:
            print(f"Safe render error: {e}")
            # Fallback to a simple message
            try:
                return font.render("[Text content]", True, color)
            except:
                return font.render("MESSAGE", True, color)
    def get_participant_name(self, message):
        """Get participant name for group messages from contacts or fallback to phone"""
        if message.get('fromMe', False):
            return 'You'
        
        # Check if this is a group chat
        if not self.current_chat or not self.current_chat.get('isGroup', False):
            return str(self.current_chat.get('name', 'Contact'))[:8] if self.current_chat else 'Contact'
        
        # For group messages, try to get participant info
        participant_id = message.get('author', '') or message.get('participant', '') or message.get('from', '')
        
        if not participant_id:
            return 'Unknown'
        
        # First try to find in contacts by ID
        for contact in self.contacts:
            if contact.get('id', '') == participant_id:
                return str(contact.get('name', ''))[:10]
        
        # If not found in contacts, try to extract phone number from participant_id
        # WhatsApp IDs are usually in format: phone@c.us or phone@g.us
        if '@' in participant_id:
            phone = participant_id.split('@')[0]
            # Clean up phone number for display
            if phone.startswith('+'): 
                return phone[:12]  # Limit length
            elif phone.isdigit() and len(phone) > 7:
                return '+' + phone[:11]  # Add + and limit length
        
        # Fallback to truncated participant ID
        return str(participant_id)[:10]
    def load_chat_messages(self, chat):
        """Load messages for selected chat and filter unsupported content"""
        def load():
            try:
                if not chat or not chat.get("id"):
                    self.error_message = "Invalid chat selected"
                    return
                    
                chat_id = chat.get("id", "").replace("@", "%40")
                
                # Try to load existing messages first
                response = requests.get(f"{self.backend_url}/chat/{chat_id}", timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        # Get all messages from the response
                        messages = []
                        
                        # Check different possible message locations in the response
                        if "messages" in data and data["messages"]:
                            messages = data.get("messages", [])
                            print(f"DEBUG: Found {len(messages)} messages in data.messages")
                        elif "chat" in data and data["chat"].get("messages"):
                            messages = data["chat"].get("messages", [])
                            print(f"DEBUG: Found {len(messages)} messages in data.chat.messages")
                        elif "chat" in data and data["chat"].get("lastMessage"):
                            # Try multiple endpoints to get full conversation history
                            try:
                                # Try endpoint 1: /chat/{id}/messages
                                history_response = requests.get(f"{self.backend_url}/chat/{chat_id}/messages", timeout=15)
                                if history_response.status_code == 200:
                                    history_data = history_response.json()
                                    if history_data.get("success", False) and history_data.get("messages"):
                                        messages = history_data.get("messages", [])
                                        print(f"DEBUG: Got {len(messages)} messages from /chat/{chat_id}/messages")
                                    else:
                                        # Try endpoint 2: /api/chat/{id}/history  
                                        history_response2 = requests.get(f"{self.backend_url}/api/chat/{chat_id}/history", timeout=15)
                                        if history_response2.status_code == 200:
                                            history_data2 = history_response2.json()
                                            if history_data2.get("success", False) and history_data2.get("messages"):
                                                messages = history_data2.get("messages", [])
                                                print(f"DEBUG: Got {len(messages)} messages from history endpoint 2")
                                            else:
                                                messages = [data["chat"].get("lastMessage")]
                                                print("DEBUG: Using only lastMessage (no history)")
                                        else:
                                            messages = [data["chat"].get("lastMessage")]
                                            print("DEBUG: History endpoint 2 failed, using lastMessage")
                                else:
                                    messages = [data["chat"].get("lastMessage")]
                                    print("DEBUG: History endpoint 1 failed, using lastMessage")
                            except Exception as ex:
                                print(f"DEBUG: Exception getting history: {ex}")
                                messages = [data["chat"].get("lastMessage")]
                                print("DEBUG: Exception getting history, using lastMessage")
                        
                        # If still no messages, try one more endpoint for archived conversations
                        if not messages:
                            try:
                                archived_response = requests.get(f"{self.backend_url}/api/conversations/{chat_id}", timeout=10)
                                if archived_response.status_code == 200:
                                    archived_data = archived_response.json()
                                    if archived_data.get("messages"):
                                        messages = archived_data.get("messages", [])
                                        print(f"DEBUG: Got {len(messages)} messages from archived conversations")
                            except:
                                pass  # Continue with empty messages
                        
                        # Filter valid text messages
                        filtered_messages = []
                        for msg in messages:
                            if msg and msg.get("body"):
                                filtered_text = self.filter_text_only(msg.get("body"))
                                if filtered_text and filtered_text not in ["[Non-text content]", "[Filtered content]"]:
                                    # Ensure message has required fields
                                    formatted_msg = {
                                        "id": msg.get("id", str(time.time())),
                                        "body": msg.get("body"),
                                        "fromMe": msg.get("fromMe", False),
                                        "timestamp": msg.get("timestamp", int(time.time())),
                                        "type": msg.get("type", "chat"),
                                        "author": msg.get("author", ""),
                                        "participant": msg.get("participant", "")
                                    }
                                    filtered_messages.append(formatted_msg)
                        
                        print(f"DEBUG: Filtered to {len(filtered_messages)} valid messages")
                        
                        # Sort messages by timestamp to ensure proper order
                        if filtered_messages:
                            try:
                                filtered_messages.sort(key=lambda x: int(x.get("timestamp", 0)))
                            except:
                                pass  # Keep original order if sorting fails
                        
                        self.current_messages = filtered_messages
                        self.current_chat = chat
                        self.mode = "chat_view"
                        self.message_scroll = 0  # Reset scroll on new chat
                        
                        if filtered_messages:
                            self.status_message = f"Chat: {chat.get('name', 'Unknown')} - {len(filtered_messages)} messages"
                        else:
                            self.status_message = f"Chat: {chat.get('name', 'Unknown')} - No messages found"
                        
                        self.error_message = ""
                        return
                
                # If API call failed, show error but still allow new conversation
                print(f"DEBUG: API call failed with status {response.status_code if response else 'None'}")
                
                # Create a new chat conversation for new contacts
                self.current_messages = [
                    {
                        "id": "system1",
                        "body": f"Starting conversation with {chat.get('name', 'Unknown')}",
                        "timestamp": int(time.time()),
                        "fromMe": False,
                        "type": "system"
                    }
                ]
                self.current_chat = chat
                self.mode = "chat_view"
                self.message_scroll = 0
                self.status_message = f"New Chat: {chat.get('name', 'Unknown')}"
                self.error_message = ""
                    
            except Exception as e:
                self.error_message = f"Load error: {str(e)[:30]}"
                print(f"DEBUG: Load error: {e}")
        
        self.status_message = "Loading chat..."
        threading.Thread(target=load, daemon=True).start()
    def send_message(self, message):
        """Send message to current chat"""
        def send():
            try:
                if not self.current_chat or not message.strip():
                    return
                
                chat_id = self.current_chat.get("id", "")
                
                # Use the send-message endpoint directly
                data = {"to": chat_id, "message": message.strip()}
                
                self.status_message = "Sending message..."
                response = requests.post(f"{self.backend_url}/send-message", json=data, timeout=15)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success", False):
                        self.status_message = "Message sent!"
                        # Add message to current messages
                        new_message = {
                            "body": message.strip(),
                            "fromMe": True,
                            "timestamp": int(time.time() * 1000)
                        }
                        self.current_messages.append(new_message)
                        # Keep reasonable number of messages
                        if len(self.current_messages) > 15:
                            self.current_messages = self.current_messages[-100:]
                        self.error_message = ""
                    else:
                        self.error_message = result.get("error", "Failed to send message")
                else:
                    self.error_message = "Failed to send message"
                    
            except Exception as e:
                self.error_message = f"Send error: {str(e)[:30]}"
                print(f"DEBUG: Send error: {e}")
        
        threading.Thread(target=send, daemon=True).start()
        
    def handle_events(self, event):
        """Main event handler for LightBerry OS"""
        return self.handle_event(event)
    
    def handle_event(self, event):
        """Handle input events"""
        if event.type != pygame.KEYDOWN:
            return None
        
        try:
            # Global ESC handling
            if event.key == pygame.K_ESCAPE:
                if self.compose_mode:
                    self.compose_mode = False
                    self.message_input = ""
                    self.input_lines = []
                elif self.mode == "chat_view":
                    # Go back to where we came from
                    if hasattr(self, '_came_from_search') and self._came_from_search:
                        self.mode = "contact_search"
                        self._came_from_search = False
                    else:
                        self.mode = "chat_list"
                    self.current_chat = None
                    self.current_messages = []
                elif self.mode == "contact_search":
                    self.mode = "main_menu"
                    self.search_input = ""
                    self.search_results = []
                elif self.mode in ["chat_list", "smart_sync"]:
                    self.mode = "main_menu"
                elif self.mode == "main_menu":
                    return "back"  # Return to LightBerry main menu
                elif self.mode in ["error", "welcome", "loading"]:
                    return "back"
                return None
            
            # Mode-specific handling
            if self.mode == "welcome":
                # Any key skips welcome
                self.mode = "loading"
                self.status_message = "Loading data"
                self.manual_smart_sync()
                
            elif self.mode == "loading":
                # No input during loading
                pass
                
            elif self.mode == "main_menu":
                self.handle_main_menu_input(event)
                
            elif self.mode == "chat_list":
                self.handle_chat_list_input(event)

            elif self.mode == "contact_search":
                self.handle_contact_search_input(event)

            elif self.mode == "smart_sync":
                self.handle_smart_sync_input(event)
            elif self.mode == "reset_account_info":
                self.handle_reset_account_info_input(event)
                
            elif self.mode == "chat_view":
                if self.compose_mode:
                    self.handle_compose_input(event)
                else:
                    self.handle_chat_view_input(event)
                    
            elif self.mode == "error":
                if event.key == pygame.K_SPACE:
                    self.mode = "loading"
                    self.manual_smart_sync()
            
        except Exception as e:
            # Never crash on input errors
            self.error_message = f"Input error: {str(e)[:30]}"
        
        return None
    def handle_main_menu_input(self, event):
        """Handle main menu navigation - now with 4 options"""
        if event.key == pygame.K_UP:
            self.selected_menu_index = max(0, self.selected_menu_index - 1)
        elif event.key == pygame.K_DOWN:
            self.selected_menu_index = min(3, self.selected_menu_index + 1)  # 0=Chat List, 1=New Chat, 2=Smart Sync, 3=Reset Account
        elif event.key == pygame.K_RETURN:
            if not self.data_loaded and self.selected_menu_index != 2:  # Allow Smart Sync even if data not loaded
                self.error_message = "Data not loaded yet"
                return
                
            if self.selected_menu_index == 0:  # Chat List
                if len(self.chats) > 0:
                    self.mode = "chat_list"
                    self.selected_chat_index = 0
                else:
                    self.error_message = "No chats available"
            elif self.selected_menu_index == 1:  # New Chat
                if len(self.contacts) > 0:
                    self.mode = "contact_search"
                    self.search_input = ""
                    self.search_results = []
                    self.selected_contact_index = 0
                else:
                    self.error_message = "No contacts available"
            elif self.selected_menu_index == 2:  # Smart Sync
                self.mode = "smart_sync"
                self.manual_smart_sync()
            elif self.selected_menu_index == 3:  # Reset Account
                self.reset_account_data()

    def handle_smart_sync_input(self, event):
        """Handle Smart Sync screen input"""
        if event.key == pygame.K_SPACE and self.sync_complete:
            # Restart sync
            self.manual_smart_sync()
        elif event.key == pygame.K_RETURN and self.sync_complete:
            # Return to main menu
            self.mode = "main_menu"
            self.status_message = self.sync_status
    
    def handle_reset_account_info_input(self, event):
        """Handle Reset Account info screen input"""
        if event.key == pygame.K_RETURN:  # Back to main menu
            self.mode = "main_menu"
    

    
    def handle_chat_list_input(self, event):
        """Handle chat list navigation"""
        try:
            if not self.chats:
                return
                
            if event.key == pygame.K_UP:
                if self.selected_chat_index > 0:
                    self.selected_chat_index -= 1
                    
            elif event.key == pygame.K_DOWN:
                if self.selected_chat_index < len(self.chats) - 1:
                    self.selected_chat_index += 1
                    
            elif event.key == pygame.K_RETURN:
                if 0 <= self.selected_chat_index < len(self.chats):
                    selected_chat = self.chats[self.selected_chat_index]
                    self.load_chat_messages(selected_chat)
                    
            elif event.key == pygame.K_r:
                # Quick refresh - use Smart Sync
                self.mode = "smart_sync"
                self.manual_smart_sync()
                
        except Exception as e:
            self.error_message = f"Navigation error: {str(e)[:30]}"

    def handle_contact_search_input(self, event):
        """Handle contact search input and navigation"""
        if event.key == pygame.K_BACKSPACE:
            if self.search_input:
                self.search_input = self.search_input[:-1]
                self.search_contacts(self.search_input)
                
        elif event.key == pygame.K_UP:
            if self.search_results and self.selected_contact_index > 0:
                self.selected_contact_index -= 1
                
        elif event.key == pygame.K_DOWN:
            if self.search_results and self.selected_contact_index < len(self.search_results) - 1:
                self.selected_contact_index += 1
                
        elif event.key == pygame.K_RETURN:
            if self.search_results and 0 <= self.selected_contact_index < len(self.search_results):
                selected_contact = self.search_results[self.selected_contact_index]
                self._came_from_search = True
                self.start_new_chat_with_contact(selected_contact)
                
        else:
            # Handle text input
            char = event.unicode
            if char and char.isprintable() and len(self.search_input) < 50:
                self.search_input += char
                self.search_contacts(self.search_input)
    
    def handle_chat_view_input(self, event):
        """Handle chat view navigation with proper scrolling"""
        if event.key == pygame.K_UP:
            # Scroll up (show older messages)
            if self.message_scroll > 0:
                self.message_scroll -= 1
        elif event.key == pygame.K_DOWN:
            # Scroll down (show newer messages)
            # Calculate maximum scroll based on total messages and visible area
            available_height = 170 - 50  # messages_end_y - messages_start_y
            line_height = 18
            max_visible_lines = available_height // line_height
            
            if len(self.current_messages) > max_visible_lines:
                max_scroll = len(self.current_messages) - max_visible_lines
                if self.message_scroll < max_scroll:
                    self.message_scroll += 1
        elif event.key == pygame.K_RETURN:
            # Enter compose mode
            self.compose_mode = True
            self.message_input = ""
            self.input_lines = []
    def handle_compose_input(self, event):
        """Handle message composition with auto-expanding input"""
        if event.key == pygame.K_RETURN:
            if self.message_input.strip():
                self.send_message(self.message_input)
                self.message_input = ""
                self.input_lines = []
                self.compose_mode = False
                
        elif event.key == pygame.K_BACKSPACE:
            if self.message_input:
                self.message_input = self.message_input[:-1]
                self.update_input_lines()
                
        else:
            char = event.unicode
            if char and char.isprintable() and len(self.message_input) < 500:
                self.message_input += char
                self.update_input_lines()
    
    def update_input_lines(self):
        """Update input lines for auto-expanding text box"""
        if not self.message_input:
            self.input_lines = [""]
            return
        
        # Word wrap the input - adjusted for larger font
        max_chars_per_line = 28  # Reduced for larger font
        words = self.message_input.split()
        self.input_lines = []
        current_line = ""
        
        for word in words:
            test_line = f"{current_line} {word}".strip()
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
            else:
                if current_line:
                    self.input_lines.append(current_line)
                current_line = word
        
        if current_line:
            self.input_lines.append(current_line)
        
        if not self.input_lines:
            self.input_lines = [""]
    
    def on_enter(self):
        """Called when module is entered"""
        # NO llamar funciones que cambien el modo durante el splash
        print("📱 Módulo WhatsApp iniciado - Mostrando splash screen")
        # Resetear el tiempo de splash para asegurar que se vea
        self.splash_start_time = time.time()

    def update(self):
        """Update module state"""
        # Handle splash screen timing
        if self.mode == "splash":
            if time.time() - self.splash_start_time >= self.splash_duration:
                print("⏱️ Fin del splash WhatsApp, yendo directo al main menu...")
                self.mode = "main_menu"
                self.status_message = "WhatsApp Ready"
            return  # No hacer nada más durante el splash
        
        # Asegurar transición fluida después del splash
        if self.mode == "welcome":
            # Auto-transition after showing welcome briefly
            current_time = time.time()
            if not hasattr(self, '_welcome_start_time'):
                self._welcome_start_time = current_time
            elif current_time - self._welcome_start_time > 2.0:  # Show welcome for 2 seconds
                self.mode = "loading"
                self.status_message = "Loading data"
        
        # Lógica original de update para otros modos
        current_time = time.time()
        
        # Auto-load data after connection
        if self.connection_stable and not self.data_loaded and self.mode == "loading":
            self.load_initial_data()
        
        # Update loading animation
        if self.mode == "loading":
            self.loading_dots = (self.loading_dots + 1) % 4
            
            # Auto-timeout para loading si se queda atascado
            if not hasattr(self, '_loading_start_time'):
                self._loading_start_time = time.time()
            elif time.time() - self._loading_start_time > 8:  # 8 segundos máximo en loading
                print("⏰ Timeout en loading, forzando transición a main_menu")
                self.mode = "main_menu"
                self.status_message = "WhatsApp (timeout - offline mode)"
                self.error_message = "Connection timeout"
        
        # Auto-sync inmediato cuando llega al main menu
        if self.mode == "main_menu" and not self.data_loaded and not hasattr(self, "_auto_sync_done"):
            self._auto_sync_done = True
            print("🔄 Auto-sync ejecutándose...")
            self.mode = "smart_sync"
            self.manual_smart_sync()
            threading.Thread(target=self.manual_smart_sync, daemon=True).start()
    def draw_splash_screen(self, screen):
        """Draw splash screen with WhatsApp image"""
        try:
            screen.fill((18, 18, 18))  # Fondo negro
            
            if self.splash_image:
                screen.blit(self.splash_image, (0, 0))
                print("📱 Mostrando imagen de splash de WhatsApp")
            else:
                # Fallback con colores de WhatsApp
                screen.fill((7, 94, 84))  # Verde de WhatsApp
                
                # Logo text estilizado
                title = self.os.font_l.render("WhatsApp", True, (255, 255, 255))
                title_x = (self.screen_width - title.get_width()) // 2
                title_y = (self.screen_height - title.get_height()) // 2 - 20
                screen.blit(title, (title_x, title_y))
                
                print("📱 Usando pantalla de splash alternativa de WhatsApp")
            
            # Indicador de carga animado
            elapsed = time.time() - self.splash_start_time
            dots = "." * (int(elapsed * 2) % 4)
            loading_text = f"Cargando{dots}"
            loading_surface = self.os.font_s.render(loading_text, True, (255, 255, 255))
            loading_x = (self.screen_width - loading_surface.get_width()) // 2
            screen.blit(loading_surface, (loading_x, self.screen_height - 50))
            
            # Barra de progreso
            progress = min(1.0, elapsed / self.splash_duration)
            bar_width = 200
            bar_height = 4
            bar_x = (self.screen_width - bar_width) // 2
            bar_y = self.screen_height - 30
            
            # Fondo de la barra
            pygame.draw.rect(screen, (60, 60, 60), (bar_x, bar_y, bar_width, bar_height))
            # Progreso
            pygame.draw.rect(screen, (7, 94, 84), (bar_x, bar_y, int(bar_width * progress), bar_height))
            
        except Exception as e:
            print(f"❌ Error dibujando splash screen WhatsApp: {e}")
            # Emergency fallback
            screen.fill((7, 94, 84))
            title = self.os.font_l.render("WhatsApp", True, (255, 255, 255))
            title_x = (self.screen_width - title.get_width()) // 2
            title_y = (self.screen_height - title.get_height()) // 2
            screen.blit(title, (title_x, title_y))
    def cleanup(self):
        """Clean up resources"""
        pass
    
    def draw(self, screen):
        """Main draw method"""
        try:
            screen.fill(BACKGROUND_COLOR)
        
            if self.mode == "splash":
                self.draw_splash_screen(screen)
                return
            
            if self.mode == "welcome":
                self.draw_welcome_screen(screen)
            elif self.mode == "loading":
                self.draw_loading_screen(screen)
            elif self.mode == "main_menu":
                self.draw_main_menu(screen)
            elif self.mode == "chat_list":
                self.draw_chat_list(screen)
            elif self.mode == "contact_search":
                self.draw_contact_search(screen)
            elif self.mode == "qr_scan":
                self.draw_qr_scan(screen)
            elif self.mode == "smart_sync":
                self.draw_smart_sync(screen)
            elif self.mode == "reset_account_info":
                self.draw_reset_account_info(screen)
            elif self.mode == "chat_view":
                if self.compose_mode:
                    self.draw_compose_screen(screen)
                else:
                    self.draw_chat_view(screen)
            elif self.mode == "error":
                self.draw_error_screen(screen)
            else:
                # Fallback
                self.draw_fallback_screen(screen)
                
        except Exception as e:
            # Fallback error display
            screen.fill(BACKGROUND_COLOR)
            error_text = self.os.font_l.render("WhatsApp", True, ERROR_COLOR)
            screen.blit(error_text, (50, 100))
            help_text = self.os.font_s.render("Press ESC to return", True, TEXT_COLOR)
            screen.blit(help_text, (50, 140))
            print(f"WhatsApp draw error: {e}")  # Log the error for debugging
    
    def draw_welcome_screen(self, screen):
        """Draw welcome screen"""
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("Welcome to WhatsApp", True, TEXT_COLOR)
        title_x = (self.screen_width - title.get_width()) // 2
        screen.blit(title, (title_x, 80))
        
        loading_text = self.os.font_m.render("Initializing...", True, HIGHLIGHT_COLOR)
        loading_x = (self.screen_width - loading_text.get_width()) // 2
        screen.blit(loading_text, (loading_x, 130))
        
        skip_text = self.os.font_s.render("Press any key to continue", True, (150, 150, 150))
        skip_x = (self.screen_width - skip_text.get_width()) // 2
        screen.blit(skip_text, (skip_x, 180))
    
    def draw_loading_screen(self, screen):
        """Draw loading screen with animated dots"""
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        header_title = self.os.font_m.render("WhatsApp", True, TEXT_COLOR)
        screen.blit(header_title, (10, 10))
        
        title = self.os.font_l.render("Loading Data", True, TEXT_COLOR)
        title_x = (self.screen_width - title.get_width()) // 2
        screen.blit(title, (title_x, 80))
        
        dots = "." * (self.loading_dots + 1)
        dots_text = self.os.font_m.render(f"Please wait{dots}", True, HIGHLIGHT_COLOR)
        dots_x = (self.screen_width - dots_text.get_width()) // 2
        screen.blit(dots_text, (dots_x, 130))
        
        if self.status_message:
            status_text = self.os.font_s.render(self.status_message, True, (150, 150, 150))
            status_x = (self.screen_width - status_text.get_width()) // 2
            screen.blit(status_text, (status_x, 160))
    def draw_main_menu(self, screen):
        """Draw main menu with green header - NOW WITH 4 OPTIONS"""
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("Main Menu WhatsApp", True, TEXT_COLOR)
        screen.blit(title, (10, 8))
        
        y = 60
        menu_title = self.os.font_l.render("Options", True, TEXT_COLOR)
        screen.blit(menu_title, (50, y))
        y += 35
        
        # Option 1: Chat List
        is_selected = (self.selected_menu_index == 0)
        option_bg = pygame.Rect(30, y-5, self.screen_width-60, 28)
        if is_selected:
            pygame.draw.rect(screen, SELECTED_COLOR, option_bg)
            pygame.draw.rect(screen, ACCENT_COLOR, option_bg, 2)
        else:
            pygame.draw.rect(screen, (50, 50, 60), option_bg)
        
        option_text = self.os.font_m.render("Chat List", True, TEXT_COLOR)
        screen.blit(option_text, (40, y))
        y += 32
        
        # Option 2: New Chat
        is_selected = (self.selected_menu_index == 1)
        option_bg = pygame.Rect(30, y-5, self.screen_width-60, 28)
        if is_selected:
            pygame.draw.rect(screen, SELECTED_COLOR, option_bg)
            pygame.draw.rect(screen, ACCENT_COLOR, option_bg, 2)
        else:
            pygame.draw.rect(screen, (50, 50, 60), option_bg)
        
        option_text = self.os.font_m.render("New Chat", True, TEXT_COLOR)
        screen.blit(option_text, (40, y))
        y += 32
        
        # Option 3: Smart Sync
        is_selected = (self.selected_menu_index == 2)
        option_bg = pygame.Rect(30, y-5, self.screen_width-60, 28)
        if is_selected:
            pygame.draw.rect(screen, SELECTED_COLOR, option_bg)
            pygame.draw.rect(screen, ACCENT_COLOR, option_bg, 2)
        else:
            pygame.draw.rect(screen, (50, 50, 60), option_bg)
        
        option_text = self.os.font_m.render("Smart Sync", True, TEXT_COLOR)
        screen.blit(option_text, (40, y))
        y += 32
        
        # Option 4: Reset Account
        is_selected = (self.selected_menu_index == 3)
        option_bg = pygame.Rect(30, y-5, self.screen_width-60, 28)
        if is_selected:
            pygame.draw.rect(screen, SELECTED_COLOR, option_bg)
            pygame.draw.rect(screen, ACCENT_COLOR, option_bg, 2)
        else:
            pygame.draw.rect(screen, (50, 50, 60), option_bg)
        
        option_text = self.os.font_m.render("Reset Account", True, TEXT_COLOR)
        screen.blit(option_text, (40, y))
        
        
        # Status at bottom
        if self.status_message:
            status_y = self.screen_height - 30
            status_text = self.os.font_s.render(self.status_message, True, HIGHLIGHT_COLOR)
            screen.blit(status_text, (10, status_y))
        
        inst_text = self.os.font_tiny.render("↑↓ Navigate  Enter: Select  ESC: Exit", True, (150, 150, 150))
        screen.blit(inst_text, (10, self.screen_height - 15))

    
    def draw_qr_scan(self, screen):
        """Draw QR scan screen"""
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("Scan QR Code", True, TEXT_COLOR)
        screen.blit(title, (10, 8))
        
        # Get QR from backend
        try:
            response = requests.get(f"{self.backend_url}/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('hasQR', False):
                    qr_text = "QR Code available - check server logs"
                    qr_display = self.os.font_m.render(qr_text, True, TEXT_COLOR)
                    screen.blit(qr_display, (20, 80))
                    
                    # Show QR data (truncated)
                    qr_data = data.get('qr', '')[:50] + "..."
                    qr_info = self.os.font_s.render(qr_data, True, (150, 150, 150))
                    screen.blit(qr_info, (20, 120))
                else:
                    status = self.os.font_m.render("Generating QR code...", True, TEXT_COLOR)
                    screen.blit(status, (20, 80))
        except:
            error = self.os.font_m.render("Error getting QR code", True, ERROR_COLOR)
            screen.blit(error, (20, 80))
        
        # Instructions
        inst_text = self.os.font_s.render("Use WhatsApp app to scan QR code", True, (150, 150, 150))
        screen.blit(inst_text, (10, self.screen_height - 30))
        
        retry_text = self.os.font_s.render("SPACE: Retry  ESC: Back", True, HIGHLIGHT_COLOR)
        screen.blit(retry_text, (10, self.screen_height - 15))


    def draw_smart_sync(self, screen):
        """Draw Smart Sync screen with progress"""
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("Smart Sync", True, TEXT_COLOR)
        screen.blit(title, (10, 8))
        
        y = 60
        
        if not self.sync_complete:
            # Show progress
            progress_title = self.os.font_l.render("Synchronizing...", True, TEXT_COLOR)
            title_x = (self.screen_width - progress_title.get_width()) // 2
            screen.blit(progress_title, (title_x, y))
            y += 40
            
            # Progress bar
            bar_width = 300
            bar_height = 20
            bar_x = (self.screen_width - bar_width) // 2
            
            # Background bar
            pygame.draw.rect(screen, (60, 60, 60), (bar_x, y, bar_width, bar_height))
            
            # Progress fill
            fill_width = int((self.sync_progress / 100) * bar_width)
            if fill_width > 0:
                pygame.draw.rect(screen, SUCCESS_COLOR, (bar_x, y, fill_width, bar_height))
            
            # Progress border
            pygame.draw.rect(screen, TEXT_COLOR, (bar_x, y, bar_width, bar_height), 2)
            y += 35
            
            # Progress percentage
            percent_text = self.os.font_m.render(f"{self.sync_progress}%", True, TEXT_COLOR)
            percent_x = (self.screen_width - percent_text.get_width()) // 2
            screen.blit(percent_text, (percent_x, y))
            y += 30
            
            # Status message
            if self.sync_status:
                status_text = self.os.font_s.render(self.sync_status[:35], True, HIGHLIGHT_COLOR)
                status_x = (self.screen_width - status_text.get_width()) // 2
                screen.blit(status_text, (status_x, y))
                
        else:
            # Sync complete
            if self.error_message:
                # Error occurred
                error_title = self.os.font_l.render("Sync Failed", True, ERROR_COLOR)
                title_x = (self.screen_width - error_title.get_width()) // 2
                screen.blit(error_title, (title_x, y))
                y += 40
                
                error_text = self.os.font_s.render(self.error_message[:35], True, TEXT_COLOR)
                error_x = (self.screen_width - error_text.get_width()) // 2
                screen.blit(error_text, (error_x, y))
                y += 40
                
                retry_text = self.os.font_s.render("SPACE: Retry  ESC: Back", True, HIGHLIGHT_COLOR)
                retry_x = (self.screen_width - retry_text.get_width()) // 2
                screen.blit(retry_text, (retry_x, y))
                
            else:
                # Success
                success_title = self.os.font_l.render("Sync Complete!", True, SUCCESS_COLOR)
                title_x = (self.screen_width - success_title.get_width()) // 2
                screen.blit(success_title, (title_x, y))
                y += 40
                
                # Show results
                if self.sync_status:
                    # Split long status message
                    status_lines = []
                    words = self.sync_status.split()
                    current_line = ""
                    
                    for word in words:
                        test_line = f"{current_line} {word}".strip()
                        if len(test_line) <= 35:
                            current_line = test_line
                        else:
                            if current_line:
                                status_lines.append(current_line)
                            current_line = word
                    
                    if current_line:
                        status_lines.append(current_line)
                    
                    for line in status_lines:
                        status_text = self.os.font_s.render(line, True, HIGHLIGHT_COLOR)
                        status_x = (self.screen_width - status_text.get_width()) // 2
                        screen.blit(status_text, (status_x, y))
                        y += 20
                
                y += 20
                continue_text = self.os.font_s.render("Enter: Continue  SPACE: Sync Again", True, (150, 150, 150))
                continue_x = (self.screen_width - continue_text.get_width()) // 2
                screen.blit(continue_text, (continue_x, y))
        
        # Instructions at bottom
        if not self.sync_complete:
            inst_text = self.os.font_tiny.render("Synchronizing data... Please wait", True, (150, 150, 150))
        else:
            inst_text = self.os.font_tiny.render("ESC: Back to Main Menu", True, (150, 150, 150))
        
        screen.blit(inst_text, (10, self.screen_height - 12))
    
    def draw_reset_account_info(self, screen):
        """Draw Reset Account information screen"""
        # Green header
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("Account Reset", True, TEXT_COLOR)
        screen.blit(title, (10, 8))
        
        y = 60
        
        # Information text
        info_lines = [
            "All synchronized data has been deleted.",
            "",
            "To connect a new WhatsApp account:",
            "",
            "1. Open your web browser",
            "2. Go to: http://localhost:3333/connect/whatsapp",
            "3. Scan the QR code with WhatsApp",
            "4. Return to this app and use Smart Sync"
        ]
        
        for line in info_lines:
            if line:  # Skip empty lines for spacing
                text = self.os.font_m.render(line, True, TEXT_COLOR)
                screen.blit(text, (20, y))
            y += 25
        
        # Back button instruction
        y += 20
        back_text = self.os.font_m.render("Press ENTER to return to Main Menu", True, HIGHLIGHT_COLOR)
        back_x = (self.screen_width - back_text.get_width()) // 2
        screen.blit(back_text, (back_x, y))
        
        # Status message if any
        if self.status_message:
            status_y = self.screen_height - 30
            status_text = self.os.font_s.render(self.status_message, True, HIGHLIGHT_COLOR)
            screen.blit(status_text, (10, status_y))
    
        # Dibujar fondo de pantalla
        if self.background_image:
            screen.blit(self.background_image, (0, 0))
            overlay = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))
        else:
            screen.fill(BACKGROUND_COLOR)

    
    def draw_chat_list(self, screen):
        """Draw chat list - clean without metadata overlap"""
        self.draw_background_safely(screen)
            
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("Chat List", True, TEXT_COLOR)
        screen.blit(title, (10, 8))
        
        count_text = self.os.font_s.render(f"({len(self.chats)})", True, TEXT_COLOR)
        screen.blit(count_text, (title.get_width() + 20, 12))
        
        y = 50
        
        if not self.chats:
            no_chats = self.os.font_m.render("No chats available", True, WARNING_COLOR)
            no_chats_x = (self.screen_width - no_chats.get_width()) // 2
            screen.blit(no_chats, (no_chats_x, y + 40))
        else:
            max_visible = 6
            start_idx = max(0, min(self.selected_chat_index - max_visible // 2, 
                                   len(self.chats) - max_visible))
            end_idx = min(len(self.chats), start_idx + max_visible)
            
            for i in range(start_idx, end_idx):
                try:
                    chat = self.chats[i]
                    is_selected = (i == self.selected_chat_index)
                    
                    if is_selected:
                        sel_rect = pygame.Rect(10, y-3, self.screen_width-20, 26)
                        pygame.draw.rect(screen, SELECTED_COLOR, sel_rect)
                        pygame.draw.rect(screen, ACCENT_COLOR, sel_rect, 2)
                    
                    color = TEXT_COLOR if is_selected else HIGHLIGHT_COLOR
                    chat_name = str(chat.get("name", "Unknown"))[:30]
                    
                    unread = chat.get("unreadCount", 0)
                    if unread > 0:
                        chat_name += f" ({unread})"
                    
                    text = self.os.font_s.render(f"{i+1:2d}. {chat_name}", True, color)
                    screen.blit(text, (15, y))
                    
                    y += 25
                    
                except Exception as e:
                    continue
        
        inst_y = self.screen_height - 30
        instructions = "↑↓ Navigate  Enter: Open  R: Smart Sync  ESC: Back"
        inst_text = self.os.font_tiny.render(instructions, True, (150, 150, 150))
        screen.blit(inst_text, (10, inst_y))
        
        if self.error_message:
            error_rect = pygame.Rect(10, inst_y - 20, self.screen_width - 20, 15)
            pygame.draw.rect(screen, ERROR_COLOR, error_rect)
            error_text = self.os.font_tiny.render(self.error_message[:45], True, TEXT_COLOR)
            screen.blit(error_text, (12, inst_y - 18))
    def draw_contact_search(self, screen):
        """Draw contact search interface"""
        self.draw_background_safely(screen)
            
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("New Chat", True, TEXT_COLOR)
        screen.blit(title, (10, 8))
        
        count_text = self.os.font_s.render(f"({len(self.contacts)})", True, TEXT_COLOR)
        screen.blit(count_text, (title.get_width() + 20, 12))
        
        y = 50
        
        # Search input box
        input_rect = pygame.Rect(15, y, self.screen_width - 30, 30)
        pygame.draw.rect(screen, (40, 40, 50), input_rect)
        pygame.draw.rect(screen, (34, 139, 34), input_rect, 2)  # Green border
        
        # Search input text
        if self.search_input:
            search_display = self.search_input
            if time.time() % 1 < 0.5:  # Blinking cursor
                search_display += "_"
            input_text = self.os.font_s.render(search_display, True, TEXT_COLOR)
            screen.blit(input_text, (20, y + 8))
        else:
            placeholder = self.os.font_s.render("Type contact name...", True, (120, 120, 120))
            screen.blit(placeholder, (20, y + 8))
        
        y += 40
        
        # Search results
        if self.search_input and self.search_results:
            results_title = self.os.font_s.render(f"Results ({len(self.search_results)}):", True, HIGHLIGHT_COLOR)
            screen.blit(results_title, (15, y))
            y += 25
            
            # Show max 5 results
            max_visible = 5
            start_idx = max(0, min(self.selected_contact_index - max_visible // 2,
                                   len(self.search_results) - max_visible))
            end_idx = min(len(self.search_results), start_idx + max_visible)
            
            for i in range(start_idx, end_idx):
                try:
                    contact = self.search_results[i]
                    is_selected = (i == self.selected_contact_index)
                    
                    # Green square selector
                    if is_selected:
                        sel_rect = pygame.Rect(10, y-3, self.screen_width-20, 22)
                        pygame.draw.rect(screen, (34, 139, 34), sel_rect)  # Green background
                        pygame.draw.rect(screen, SUCCESS_COLOR, sel_rect, 2)  # Green border
                    
                    color = TEXT_COLOR if is_selected else HIGHLIGHT_COLOR
                    contact_name = str(contact.get("name", "Unknown"))[:35]
                    
                    text = self.os.font_s.render(f"{i+1:2d}. {contact_name}", True, color)
                    screen.blit(text, (15, y))
                    
                    y += 22
                    
                except Exception as e:
                    continue
                    
        elif self.search_input and not self.search_results:
            no_results = self.os.font_s.render("No contacts found", True, WARNING_COLOR)
            screen.blit(no_results, (15, y))
            
        elif not self.search_input:
            help_text = self.os.font_s.render("Start typing to search contacts...", True, (150, 150, 150))
            screen.blit(help_text, (15, y))
        
        # Instructions at bottom
        inst_y = self.screen_height - 30
        if self.search_results:
            instructions = "↑↓ Select  Enter: Chat  Backspace: Delete  ESC: Back"
        else:
            instructions = "Type to search  Backspace: Delete  ESC: Back"
        
        inst_text = self.os.font_tiny.render(instructions, True, (150, 150, 150))
        screen.blit(inst_text, (10, inst_y))
        
        if self.error_message:
            error_rect = pygame.Rect(10, inst_y - 20, self.screen_width - 20, 15)
            pygame.draw.rect(screen, ERROR_COLOR, error_rect)
            error_text = self.os.font_tiny.render(self.error_message[:45], True, TEXT_COLOR)
            screen.blit(error_text, (12, inst_y - 18))
    def draw_chat_view(self, screen):
        """Draw chat view with all messages and proper scrolling"""
        if not self.current_chat:
            return

        self.draw_background_safely(screen)

        # Header
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        chat_name = str(self.current_chat.get("name", "Unknown"))[:20]
        title = self.os.font_m.render(chat_name, True, TEXT_COLOR)
        screen.blit(title, (10, 10))

        if hasattr(self, '_came_from_search') and self._came_from_search:
            indicator = self.os.font_tiny.render("New Chat", True, (150, 255, 150))
            screen.blit(indicator, (self.screen_width - 60, 15))

        # Message display area - adjusted to not overlap with input area
        messages_start_y = 50
        messages_end_y = 170  # Leave space for input area
        line_height = 18

        if not self.current_messages:
            no_msg = self.os.font_m.render("No messages", True, HIGHLIGHT_COLOR)
            no_msg_x = (self.screen_width - no_msg.get_width()) // 2
            screen.blit(no_msg, (no_msg_x, messages_start_y + 40))
        else:
            # Calculate how many lines we can show
            available_height = messages_end_y - messages_start_y
            max_lines = available_height // line_height
            
            # Start from the end of messages (newest first) minus scroll offset
            total_messages = len(self.current_messages)
            if total_messages == 0:
                return
            
            # Calculate starting message index based on scroll
            start_msg_index = max(0, total_messages - max_lines + self.message_scroll)
            end_msg_index = min(total_messages, start_msg_index + max_lines)
            
            y = messages_start_y
            messages_to_show = self.current_messages[start_msg_index:end_msg_index]
            
            for message in messages_to_show:
                if y >= messages_end_y - line_height:
                    break
                
                try:
                    body = self.filter_text_only(message.get("body", ""))
                    
                    if message.get("fromMe", False):
                        color = SUCCESS_COLOR
                        prefix = "You: "
                    else:
                        color = HIGHLIGHT_COLOR
                        participant_name = self.get_participant_name(message)
                        prefix = f"{participant_name}: "
                    
                    # Word wrap the message to fit screen
                    full_text = prefix + body
                    max_width = self.screen_width - 30
                    
                    # Simple word wrapping
                    words = full_text.split()
                    lines = []
                    current_line = ""
                    
                    for word in words:
                        test_line = f"{current_line} {word}".strip()
                        text_width = self.os.font_s.size(test_line)[0]
                        
                        if text_width <= max_width:
                            current_line = test_line
                        else:
                            if current_line:
                                lines.append(current_line)
                            current_line = word
                    
                    if current_line:
                        lines.append(current_line)
                    
                    # Draw each line of the message
                    for line in lines:
                        if y >= messages_end_y - line_height:
                            break
                        text_surface = self.safe_render_text(line, self.os.font_s, color)
                        screen.blit(text_surface, (15, y))
                        y += line_height
                    
                    # Small gap between messages
                    y += 3
                    
                except Exception as e:
                    print(f"Error rendering message: {e}")
                    continue
        
        # Input area at bottom - fixed position
        input_start_y = 175
        input_height = 50
        input_rect = pygame.Rect(10, input_start_y, self.screen_width - 20, input_height)
        pygame.draw.rect(screen, (40, 40, 50), input_rect)
        pygame.draw.rect(screen, ACCENT_COLOR, input_rect, 2)
        
        prompt_text = self.os.font_s.render("Press Enter to compose message", True, HIGHLIGHT_COLOR)
        prompt_x = (self.screen_width - prompt_text.get_width()) // 2
        screen.blit(prompt_text, (prompt_x, input_start_y + 15))
        
        # Instructions at bottom
        scroll_info = ""
        if self.current_messages and len(self.current_messages) > max_lines:
            scroll_info = f" ({start_msg_index+1}-{end_msg_index}/{total_messages})"
        
        inst_text = self.os.font_tiny.render(f"↑↓ Scroll{scroll_info}  Enter: Compose  ESC: Back", True, (150, 150, 150))
        screen.blit(inst_text, (10, self.screen_height - 12))
    def draw_compose_screen(self, screen):
        """Draw message composition with larger text"""
        if not self.current_chat:
                return
        
        pygame.draw.rect(screen, (34, 139, 34), (0, 0, self.screen_width, 40))
        
        title = self.os.font_m.render(f"To: {str(self.current_chat.get('name', 'Unknown'))[:15]}", True, TEXT_COLOR)
        screen.blit(title, (10, 10))
        
        y = 50
        if self.current_messages:
            recent_text = self.os.font_s.render("Recent:", True, HIGHLIGHT_COLOR)
            screen.blit(recent_text, (15, y))
            y += 20
            
            # Show last 2 messages for context with larger font
            for message in self.current_messages[-2:]:
                try:
                    sender = "You" if message.get("fromMe", False) else self.get_participant_name(message)
                    body = self.filter_text_only(message.get("body", ""))[:20]  # Reduced for larger font
                    color = SUCCESS_COLOR if message.get("fromMe", False) else (180, 180, 180)
                    
                    # LARGER FONT FOR RECENT MESSAGES
                    text = self.os.font_s.render(f"{sender}: {body}", True, color)  # Changed from font_tiny
                    screen.blit(text, (20, y))
                    y += 16  # Adjusted spacing
                except:
                    continue
        
        # Input area - auto-expanding with larger font
        input_start_y = 110  # Adjusted for larger recent messages
        line_height = 20  # Increased for larger font
        padding = 10
        
        if not self.input_lines:
            self.update_input_lines()
        
        input_height = max(40, len(self.input_lines) * line_height + padding * 2)
        
        if input_start_y + input_height > self.screen_height - 30:
            input_start_y = self.screen_height - 30 - input_height
        
        input_rect = pygame.Rect(10, input_start_y, self.screen_width - 20, input_height)
        pygame.draw.rect(screen, (30, 30, 40), input_rect)
        pygame.draw.rect(screen, ACCENT_COLOR, input_rect, 2)
        
        if self.input_lines and self.input_lines[0]:
            for i, line in enumerate(self.input_lines):
                line_y = input_start_y + padding + (i * line_height)
                if line_y + line_height <= input_start_y + input_height - padding:
                    # LARGER FONT FOR INPUT TEXT
                    text = self.os.font_m.render(line, True, TEXT_COLOR)  # Changed from font_s to font_m
                    screen.blit(text, (15, line_y))
            
            if time.time() % 1 < 0.5:
                cursor_line = len(self.input_lines) - 1
                cursor_y = input_start_y + padding + (cursor_line * line_height)
                if cursor_y + line_height <= input_start_y + input_height - padding:
                    cursor_x = 15 + self.os.font_m.size(self.input_lines[-1])[0]  # Adjusted for font_m
                    cursor_text = self.os.font_m.render("_", True, SUCCESS_COLOR)  # Changed font
                    screen.blit(cursor_text, (cursor_x, cursor_y))
        else:
            # LARGER FONT FOR PLACEHOLDER
            placeholder = self.os.font_m.render("Type your message...", True, (100, 100, 100))  # Changed font
            screen.blit(placeholder, (15, input_start_y + padding))
        
        instructions = "Enter: Send  Backspace: Delete  ESC: Cancel"
        inst_text = self.os.font_tiny.render(instructions, True, (150, 150, 150))
        screen.blit(inst_text, (10, self.screen_height - 12))
    
    def draw_error_screen(self, screen):
        """Draw error screen"""
        pygame.draw.rect(screen, ERROR_COLOR, (0, 0, self.screen_width, 40))
        
        title = self.os.font_l.render("WhatsApp Error", True, TEXT_COLOR)
        title_x = (self.screen_width - title.get_width()) // 2
        screen.blit(title, (title_x, 8))
        
        if self.error_message:
            y = 80
            words = self.error_message.split()
            lines = []
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if len(test_line) <= 30:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                error_text = self.os.font_s.render(line, True, TEXT_COLOR)
                error_x = (self.screen_width - error_text.get_width()) // 2
                screen.blit(error_text, (error_x, y))
                y += 25
        
        y = self.screen_height - 40
        instruction = self.os.font_s.render("SPACE: Retry  ESC: Exit", True, HIGHLIGHT_COLOR)
        inst_x = (self.screen_width - instruction.get_width()) // 2
        screen.blit(instruction, (inst_x, y))
    
    def draw_fallback_screen(self, screen):
        """Emergency fallback screen"""
        title = self.os.font_l.render("WhatsApp", True, ACCENT_COLOR)
        title_x = (self.screen_width - title.get_width()) // 2
        screen.blit(title, (title_x, 100))
        
        instruction = self.os.font_s.render("Press ESC to return", True, TEXT_COLOR)
        inst_x = (self.screen_width - instruction.get_width()) // 2
        screen.blit(instruction, (inst_x, 150))


# Main execution function for terminal and ColorBerry display
def main():
    """Main function to run WhatsApp with full interface"""
    import os
    import sys
    
    # Check if running on ColorBerry display
    display_mode = os.environ.get('DISPLAY', '') or 'headless'
    if display_mode == 'headless':
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
    
    pygame.init()
    
    # Create display window
    if display_mode != 'headless':
        # Para ColorBerry - pantalla real
        screen = pygame.display.set_mode((400, 240))
        pygame.display.set_caption("WhatsApp - ColorBerry Mode")
    else:
        # Para terminal - pantalla virtual
        screen = pygame.display.set_mode((400, 240))
        pygame.display.set_caption("WhatsApp - Terminal Mode")
    
    clock = pygame.time.Clock()
    
    # Create WhatsApp instance
    whatsapp = WhatsApp()
    
    print("🚀 Starting WhatsApp with full interface...")
    print("📱 WhatsApp Module initialized")
    print("🌐 Connecting to server at http://localhost:3333")
    print("🖥️ Display mode:", display_mode)
    
    # Test server connection
    try:
        import requests
        response = requests.get("http://localhost:3333/status", timeout=5)
        if response.status_code == 200:
            print("✅ Server connection successful")
            status = response.json()
            print(f"📊 Status: {status.get('status', 'Unknown')}")
            print(f"🔐 Authenticated: {status.get('authenticated', False)}")
        else:
            print(f"⚠️ Server responded with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
    
    if display_mode != 'headless':
        print("🖥️ Interface will be displayed on ColorBerry screen")
        print("📋 Use keyboard/mouse to interact")
    else:
        print("📋 Running in headless mode - Use Ctrl+C to exit")
    
    running = True
    frame_count = 0
    last_mode = ""
    
    try:
        while running:
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and whatsapp.mode == "splash":
                        running = False
                    else:
                        result = whatsapp.handle_event(event)
                        if result == "back":
                           running = False
            
            # Update WhatsApp
            whatsapp.update()
            
            # Draw everything with full interface
            screen.fill(BACKGROUND_COLOR)
            whatsapp.draw(screen)
            
            pygame.display.flip()
            clock.tick(60)
            
            # Status updates
            frame_count += 1
            if frame_count % 300 == 0:  # Every 5 seconds
                if whatsapp.mode != last_mode:
                    print(f"📊 WhatsApp Mode: {whatsapp.mode}")
                    if whatsapp.mode == "main_menu":
                        print("📋 Main Menu: Use arrow keys to navigate, Enter to select")
                    elif whatsapp.mode == "chat_list":
                        print("💬 Chat List: Use arrow keys to navigate, Enter to open chat")
                    elif whatsapp.mode == "chat_view":
                        print("📱 Chat View: Type to compose message, Enter to send")
                    last_mode = whatsapp.mode
                
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
        running = False
    
    pygame.quit()
    print("👋 WhatsApp interface closed")

if __name__ == "__main__":
    main()
