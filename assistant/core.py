import datetime
from interfaces.gui import AssistantApp
class Assistant:
    """
    The core "brain" of the assistant.

    This class is responsible for processing text commands and returning a
    text-based response. It is completely decoupled from any user interface
    (GUI, voice, etc.), which makes the system modular and easy to test.
    """
    def __init__(self):
        # You can initialize any required resources here.
        # For example, loading a machine learning model, connecting to a database, etc.
        pass

    def process_command(self, command_text: str) -> str:
        """
        Processes a given text command and returns a response.

        Args:
            command_text (str): The user's command, converted to lowercase text.

        Returns:
            str: The assistant's text response.
        """
        command_text = command_text.lower()

        # --- Basic Command Handling ---
        # We use simple `if/elif` statements for now.
        # As your assistant grows, you might want to use a more advanced
        # intent recognition system.

        if "hello" in command_text or "hi" in command_text:
            return "Hello there! How can I assist you today?"

        elif "time" in command_text:
            now = datetime.datetime.now()
            return f"The current time is {now.strftime('%I:%M %p')}."

        elif "date" in command_text:
            today = datetime.date.today()
            return f"Today's date is {today.strftime('%B %d, %Y')}."

        elif "your name" in command_text:
            # You can configure the assistant's name in `config.py`
            # For now, we'll hardcode it.
            return "I am a helpful assistant created for your Final Year Project."

        elif "exit" in command_text or "quit" in command_text:
            return "Goodbye!"

        else:
            # Default response for unrecognized commands
            return "I'm sorry, I didn't understand that. Can you please rephrase?"
    # assistant/core.py

    def run(self):
        print("Assistant is running...")
        AssistantApp().run()