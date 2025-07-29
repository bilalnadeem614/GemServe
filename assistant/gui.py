from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from assistant.voice import listen_and_transcribe, speak
from assistant.llm import ask_gemma

class AssistantGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=10, spacing=10, **kwargs)

        self.output = Label(size_hint_y=None, text='Listening.', halign='left', valign='top')
        self.output.bind(texture_size=self._update_label_height)
        scroll = ScrollView(size_hint=(1, 0.7))
        scroll.add_widget(self.output)

        self.btn_listen = Button(text='🎤 Speak', size_hint=(1, 0.15))
        self.btn_listen.bind(on_press=self.start_voice_thread)

        self.add_widget(scroll)
        self.add_widget(self.btn_listen)

    def _update_label_height(self, instance, value):
        self.output.height = self.output.texture_size[1]

    def start_voice_thread(self, instance):
        import threading
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: self.set_output_text('🎙 Listening...'))
        threading.Thread(target=self.process_voice, daemon=True).start()

    def set_output_text(self, text):
        self.output.text = text
        self.canvas.ask_update()

    def append_output_text(self, text):
        self.output.text += text
        self.canvas.ask_update()

    def process_voice(self):
        from kivy.clock import Clock
        try:
            prompt = listen_and_transcribe()
            Clock.schedule_once(lambda dt: self.set_output_text(f"📝 You said: {prompt}\n"))
            response = ask_gemma(prompt)
            Clock.schedule_once(lambda dt: self.append_output_text(f"🤖 Gemma3n: {response}"))
            speak(response)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.set_output_text(f"❌ Error: {e}"))

class AssistantApp(App):
    def build(self):
        return AssistantGUI()
