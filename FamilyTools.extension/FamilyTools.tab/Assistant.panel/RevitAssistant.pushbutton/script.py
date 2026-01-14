# -*- coding: utf-8 -*-
from pyrevit import script, revit, forms
import clr
import sys
import os
import json
import urllib2

# Add WPF references
clr.AddReference("PresentationFramework")
clr.AddReference("System.Windows")
from System.Windows import Application, Window

# --- Ollama Client ---
class OllamaClient:
    def __init__(self, model="qwen2.5-coder:32b", host="http://localhost:11434"):
        self.model = model
        self.host = host
        self.generate_endpoint = "{}/api/generate".format(self.host)

    def generate(self, prompt, system_prompt=None):
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            data["system"] = system_prompt

        req = urllib2.Request(self.generate_endpoint)
        req.add_header('Content-Type', 'application/json')
        
        try:
            response = urllib2.urlopen(req, json.dumps(data))
            result = json.load(response)
            return result.get("response", "")
        except Exception as e:
            return "Error: {}".format(str(e))

# --- UI Class ---
class RevitAssistantWindow(forms.WPFWindow):
    def __init__(self, xaml_file):
        forms.WPFWindow.__init__(self, xaml_file)
        
        # Controls (WPFWindow automatically sets up self from xaml names if they match)
        # But we can access them via FindName or just self.Name if xaml is loaded correctly
        self.chat_history = self.ChatHistory
        self.input_box = self.InputBox
        self.send_button = self.SendButton
        self.status_text = self.StatusText

        # Events
        self.send_button.Click += self.send_click
        
        # Ollama
        self.client = OllamaClient()

        # Show
        self.Show()

    def add_message(self, text, sender="User"):
        from System.Windows.Controls import TextBlock, Border
        from System.Windows import Thickness, CornerRadius
        from System.Windows.Media import Brushes, SolidColorBrush, Color
        
        # Create message container
        border = Border()
        border.CornerRadius = CornerRadius(5)
        border.Padding = Thickness(10)
        border.Margin = Thickness(0, 0, 0, 5)
        
        text_block = TextBlock()
        text_block.Text = text
        text_block.TextWrapping = 2 # Wrap
        
        if sender == "User":
            border.Background = SolidColorBrush(Color.FromRgb(220, 248, 198)) # Light Green
            border.HorizontalAlignment = 2 # Right
            text_block.Foreground = Brushes.Black
        else:
            border.Background = SolidColorBrush(Color.FromRgb(240, 240, 240)) # Light Gray
            border.HorizontalAlignment = 0 # Left
            text_block.Foreground = Brushes.Black

        border.Child = text_block
        self.chat_history.Children.Add(border)
        
        # Scroll to bottom
        scroll = self.ChatScroll
        scroll.ScrollToBottom()

    def send_click(self, sender, args):
        user_input = self.input_box.Text
        if not user_input:
            return

        self.add_message(user_input, "User")
        self.input_box.Text = ""
        self.status_text.Text = "Thinking..."
        
        # Run in background to avoid freezing UI? 
        # IronPython WPF threading is tricky. For now, simple synchronous call.
        try:
            # System prompt to guide the model for Revit API
            sys_prompt = "You are a Revit API expert using Python (IronPython 2.7). Write code to accomplish the user request. Wrap code in ```python blocks. Do not use type hints or f-strings."
            
            response = self.client.generate(user_input, system_prompt)
            self.add_message(response, "Assistant")
            
            # Check for code blocks
            if "```python" in response:
                self.add_code_run_button(response)
                
        except Exception as e:
            self.add_message("Error: " + str(e), "System")
            
        self.status_text.Text = "Ready"

    def add_code_run_button(self, response):
        from System.Windows.Controls import Button
        from System.Windows import Thickness
        
        # Parse code
        import re
        code_blocks = re.findall(r'```python(.*?)```', response, re.DOTALL)
        
        if code_blocks:
            code = code_blocks[0].strip()
            
            btn = Button()
            btn.Content = "Run Generated Code"
            btn.Width = 150
            btn.Margin = Thickness(5)
            btn.Click += lambda s, e: self.run_generated_code(code)
            
            self.chat_history.Children.Add(btn)

    def run_generated_code(self, code):
        try:
            self.status_text.Text = "Running code..."
            # Execute the code
            exec(code)
            self.status_text.Text = "Code executed successfully."
            forms.alert("Code executed successfully!")
        except Exception as e:
            self.status_text.Text = "Execution Error"
            forms.alert("Error executing code: " + str(e))

# --- Run ---
xaml_file = script.get_bundle_file("ui.xaml")
# PyRevit WPFWindow handles loading the XAML
RevitAssistantWindow(xaml_file)
