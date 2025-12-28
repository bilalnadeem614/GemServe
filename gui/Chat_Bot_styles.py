
def get_chat_styles(dark_mode):
    scroll_style = """
            QScrollArea#chatArea {
                border: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
                margin: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(139, 92, 246, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(139, 92, 246, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """
        
    if dark_mode:
        return scroll_style + """
                /* Main Background */
                QWidget {
                    background-color: #0A0E27;
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                /* Header */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #6366F1);
                    border: none;
                }
                
                QPushButton#backButton {
                    background: rgba(255, 255, 255, 0.15);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 20px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton#backButton:hover {
                    background: rgba(255, 255, 255, 0.25);
                }
                
                QLabel#headerTitle {
                    color: #FFFFFF;
                    font-size: 22px;
                    font-weight: 800;
                    letter-spacing: -0.5px;
                    background: transparent;
                }
                
                /* Files Container */
                QFrame#filesContainer {
                    background: rgba(139, 92, 246, 0.08);
                    border: 2px solid rgba(139, 92, 246, 0.2);
                    border-radius: 12px;
                }
                
                QLabel#filesTitle {
                    color: #A78BFA;
                    font-size: 13px;
                    font-weight: 700;
                    background: transparent;
                }
                
                QLabel#fileBadge {
                    background: rgba(30, 41, 59, 0.6);
                    color: #C4B5FD;
                    border: 1.5px solid rgba(139, 92, 246, 0.3);
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 600;
                }
                
                /* Chat Area */
                QWidget#chatContainer {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0F172A, stop:1 #0A0E27);
                }
                
                /* Input Frame */
                QFrame#inputFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #0F172A, stop:1 #0A0E27);
                    border-top: 2px solid rgba(139, 92, 246, 0.2);
                }
                
                /* Input Wrapper with Perfect Border Radius */
                QFrame#inputWrapper {
                    background: rgba(30, 41, 59, 0.6);
                    border: 2.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 27px;
                }
                
                /* Message Input */
                QLineEdit#messageInput {
                    border: none;
                    background: transparent;
                    color: #E2E8F0;
                    font-size: 16px;
                    font-weight: 500;
                }
                
                QLineEdit#messageInput:focus {
                    border: none;
                }
                
                QLineEdit#messageInput::placeholder {
                    color: #64748B;
                    font-style: italic;
                }

                
                /* Mode Combo */
                QComboBox#modeCombo {
                    background: rgba(30, 41, 59, 0.8);
                    border: 2px solid rgba(139, 92, 246, 0.4);
                    border-radius: 18px;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 600;
                    color: #E2E8F0;
                }
                QComboBox#modeCombo::drop-down {
                    border: none;
                    padding-right: 8px;
                    width: 20px;
                }
                QComboBox#modeCombo::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #A78BFA;
                    margin-right: 8px;
                }
                QComboBox#modeCombo:hover {
                    border: 2px solid #8B5CF6;
                    background: rgba(139, 92, 246, 0.15);
                }
                QComboBox#modeCombo QAbstractItemView {
                    background: rgba(30, 41, 59, 0.95);
                    border: 2px solid rgba(139, 92, 246, 0.4);
                    border-radius: 12px;
                    padding: 8px;
                    selection-background-color: rgba(139, 92, 246, 0.25);
                    selection-color: #FFFFFF;
                    font-size: 13px;
                    font-weight: 600;
                    outline: none;
                    color: #E2E8F0;
                }
                QComboBox#modeCombo QAbstractItemView::item {
                    padding: 8px 12px;
                    border-radius: 8px;
                    min-height: 30px;
                    color: #E2E8F0;
                }
                QComboBox#modeCombo QAbstractItemView::item:hover {
                    background: rgba(139, 92, 246, 0.2);
                    color: #FFFFFF;
                }
                QComboBox#modeCombo QAbstractItemView::item:selected {
                    background: rgba(139, 92, 246, 0.25);
                    color: #FFFFFF;
                }
                /* Icon Buttons */
                QPushButton#iconButton {
                    background: rgba(139, 92, 246, 0.15);
                    border: none;
                    border-radius: 18px;
                    font-size: 18px;
                }
                
                QPushButton#iconButton:hover {
                    background: rgba(139, 92, 246, 0.3);
                }
                
                /* Send Button with Perfect Border Radius */
                QPushButton#sendButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    color: #FFFFFF;
                    font-weight: 800;
                    font-size: 16px;
                    border: none;
                    border-radius: 27px;
                }
                
                QPushButton#sendButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #8B5CF6);
                }
                
                QPushButton#sendButton:disabled {
                    background: rgba(71, 85, 105, 0.4);
                    color: #64748B;
                }
            """
    else:
        return scroll_style + """
                /* Main Background */
                QWidget {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F8FAFC, stop:1 #EFF6FF);
                    font-family: 'Inter', 'Segoe UI Variable', sans-serif;
                }
                
                /* Header */
                QFrame#header {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #6366F1);
                    border: none;
                }
                
                QPushButton#backButton {
                    background: rgba(255, 255, 255, 0.2);
                    color: #FFFFFF;
                    border: none;
                    border-radius: 20px;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton#backButton:hover {
                    background: rgba(255, 255, 255, 0.35);
                }
                
                QLabel#headerTitle {
                    color: #FFFFFF;
                    font-size: 22px;
                    font-weight: 800;
                    letter-spacing: -0.5px;
                    background: transparent;
                }
                
                /* Files Container */
                QFrame#filesContainer {
                    background: rgba(245, 243, 255, 0.8);
                    border: 2px solid rgba(139, 92, 246, 0.15);
                    border-radius: 12px;
                }
                
                QLabel#filesTitle {
                    color: #7C3AED;
                    font-size: 13px;
                    font-weight: 700;
                    background: transparent;
                }
                
                QLabel#fileBadge {
                    background: #FFFFFF;
                    color: #7C3AED;
                    border: 1.5px solid rgba(139, 92, 246, 0.25);
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 13px;
                    font-weight: 600;
                }
                
                /* Chat Area */
                QWidget#chatContainer {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #F8FAFC, stop:1 #EFF6FF);
                }
                

                /* Mode Combo */
                QComboBox#modeCombo {
                background: white;
                border: 2px solid rgba(139, 92, 246, 0.3);
                border-radius: 18px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 600;
                color: #6366F1;
                }

                QComboBox#modeCombo::drop-down {
                border: none;
                padding-right: 8px;
                width: 20px;
                }

                QComboBox#modeCombo::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6366F1;
                margin-right: 8px;
                }
                QComboBox#modeCombo:hover {
                border: 2px solid #8B5CF6;
                background: rgba(139, 92, 246, 0.05);
                }
                QComboBox#modeCombo QAbstractItemView {
                background: white;
                border: 2px solid rgba(139, 92, 246, 0.3);
                border-radius: 12px;
                padding: 8px;
                selection-background-color: rgba(139, 92, 246, 0.15);
                selection-color: #1E293B;
                font-size: 13px;
                font-weight: 600;
                outline: none;
                color: #1E293B;
                }
                QComboBox#modeCombo QAbstractItemView::item {
                padding: 8px 12px;
                border-radius: 8px;
                min-height: 30px;
                color: #1E293B;
                }
                QComboBox#modeCombo QAbstractItemView::item:hover {
                background: rgba(139, 92, 246, 0.1);
                color: #000000;
                }
                QComboBox#modeCombo QAbstractItemView::item:selected {
                background: rgba(139, 92, 246, 0.15);
                color: #000000;
                }


                /* Input Frame */
                QFrame#inputFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #FFFFFF, stop:1 #F8FAFC);
                    border-top: 2px solid rgba(139, 92, 246, 0.15);
                }
                
                /* Input Wrapper with Perfect Border Radius */
                QFrame#inputWrapper {
                    background: #FFFFFF;
                    border: 2.5px solid rgba(226, 232, 240, 0.8);
                    border-radius: 27px;
                }
                
                /* Message Input */
                QLineEdit#messageInput {
                    border: none;
                    background: transparent;
                    color: #0F172A;
                    font-size: 16px;
                    font-weight: 500;
                }
                
                QLineEdit#messageInput:focus {
                    border: none;
                }
                
                QLineEdit#messageInput::placeholder {
                    color: #94A3B8;
                    font-style: italic;
                }
                
                /* Icon Buttons */
                QPushButton#iconButton {
                    background: rgba(139, 92, 246, 0.08);
                    border: none;
                    border-radius: 18px;
                    font-size: 18px;
                }
                
                QPushButton#iconButton:hover {
                    background: rgba(139, 92, 246, 0.15);
                }
                
                /* Send Button with Perfect Border Radius */
                QPushButton#sendButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A78BFA);
                    color: #FFFFFF;
                    font-weight: 800;
                    font-size: 16px;
                    border: none;
                    border-radius: 27px;
                }
                
                QPushButton#sendButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #8B5CF6);
                }
                
                QPushButton#sendButton:disabled {
                    background: #E2E8F0;
                    color: #94A3B8;
                }
            """