import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from urllib.parse import urlparse, parse_qs, unquote

class CurlJSONFormatterApp:
    def __init__(self, root):
        self.root = root
        self.history = []
        self.future = []

        self.setup_ui()

        # Bindings for undo and redo on macOS
        self.root.bind('<Command-z>', self.undo)
        self.root.bind('<Command-Shift-Z>', self.redo)

        # Detect changes in the curl input area


    def setup_ui(self):
        self.root.title("Curl JSON Formatter")
        self.root.geometry("1000x1000")
        self.root.resizable(True, True)

        # Status code label
        self.status_label = tk.Label(self.root, text="Status Code: N/A", font=('Arial', 14))
        self.status_label.pack(pady=(10, 0))

        # Curl input label and text area
        tk.Label(self.root, text="Enter curl command:").pack(pady=(10, 0))
        self.curl_input = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=110, height=8)
        self.curl_input.pack(padx=10, pady=(0, 10))

        # Request type selector
        tk.Label(self.root, text="Select Request Type:").pack(pady=(10, 0))
        self.request_type = ttk.Combobox(self.root, values=["GET", "POST"], state="readonly")
        self.request_type.current(0)  # Set default to GET
        self.request_type.pack(pady=(0, 10))

        # Execute and Copy button
        self.execute_and_copy_button = tk.Button(self.root, text="Execute Curl & Copy", command=self.execute_and_copy_curl)
        self.execute_and_copy_button.pack(pady=(0, 10))

        # Clear Curl Field button
        self.clear_curl_button = tk.Button(self.root, text="Clear Curl Field", command=self.clear_curl_field)
        self.clear_curl_button.pack(pady=(0, 10))
        
        self.extract_button = tk.Button(self.root, text="Extract Variables from CURL", command=self.extract_variables_from_curl)
        self.extract_button.pack(pady=(0, 10))

        # Output label and text area
        tk.Label(self.root, text="Formatted Structure:").pack(pady=(10, 0))
        self.output_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=110, height=15)
        self.output_text.pack(padx=10, pady=(0, 10))

        # PHP Code Output area (initially hidden)
        self.php_code_var = tk.BooleanVar()
        self.show_php_code_checkbox = tk.Checkbutton(self.root, text="Show PHP Code", variable=self.php_code_var, command=self.toggle_php_code)
        self.show_php_code_checkbox.pack(pady=(10, 0))

        self.query_output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=110, height=10)
        self.query_output.pack(padx=10, pady=(0, 10))
        self.query_output.pack_forget()  # Initially hide

        # Checkbox to toggle raw JSON visibility
        self.show_json_var = tk.BooleanVar()
        self.show_json_checkbox = tk.Checkbutton(self.root, text="Show Raw JSON Output", variable=self.show_json_var, command=self.toggle_raw_json)
        self.show_json_checkbox.pack(pady=(10, 0))

        # Checkbox to toggle pretty JSON output
        self.pretty_json_var = tk.BooleanVar()
        self.pretty_json_checkbox = tk.Checkbutton(self.root, text="Toggle Pretty/Raw JSON", variable=self.pretty_json_var, command=self.toggle_json_format)
        self.pretty_json_checkbox.pack(pady=(10, 0))

        # Hidden raw JSON output area
        self.raw_json_output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=110, height=15)
        self.raw_json_output.pack_forget()

    def execute_curl(self):
        curl_command = self.curl_input.get("1.0", tk.END).strip()
        if not curl_command.startswith("curl"):
            messagebox.showerror("Error", "Please enter a valid curl command.")
            return
        
        try:
            # Execute the curl command and capture the response
            result = subprocess.run(f"{curl_command} -w '\\n%{{http_code}}'", shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                messagebox.showerror("Error", f"curl command failed with error: {result.stderr}")
                return

            # Extract the JSON string and status code from the output
            output_parts = result.stdout.rsplit("\n", 1)
            raw_json_string = output_parts[0].strip()
            status_code = output_parts[1].strip()

            # Display the status code
            self.status_label.config(text=f"Status Code: {status_code}")

            # Pretty-print JSON if needed
            pretty_json_string = json.dumps(json.loads(raw_json_string), indent=4)

            # Update the raw JSON output area
            self.raw_json_output.delete("1.0", tk.END)
            self.raw_json_output.insert(tk.END, raw_json_string)

            # Parse and format the JSON structure
            json_data = json.loads(raw_json_string)
            structure = self.parse_json_structure(json_data)
            formatted_structure = self.format_structure(structure)
            
            # Update the formatted output area
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, f"assertJsonStructure({formatted_structure})")
            
            # Automatically copy assertJsonStructure output to clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(f"assertJsonStructure({formatted_structure})")
            messagebox.showinfo("Copied", "Formatted structure copied to clipboard.")
            
            # Store raw and pretty JSON for toggle functionality
            self.raw_json_output.raw_json = raw_json_string
            self.raw_json_output.pretty_json = pretty_json_string

            # Update history
            self.add_to_history(curl_command, raw_json_string, formatted_structure)

        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to parse JSON from curl output.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

    def execute_and_copy_curl(self):
        self.execute_curl()

    def clear_curl_field(self):
        self.curl_input.delete("1.0", tk.END)

    def extract_variables_from_curl(self):
        curl_command = self.curl_input.get("1.0", tk.END).strip()
        request_type = self.request_type.get()

        try:
            if request_type == "POST":
                self.parse_post_request(curl_command)
            elif request_type == "GET":
                self.parse_get_request(curl_command)
            else:
                messagebox.showerror("Error", "Unknown request type selected.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract variables from URL: {str(e)}")

    def parse_get_request(self, curl_command):
        start = curl_command.find("http")
        url = curl_command[start:].split()[0]
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        path = parsed_url.path

        # Format the query parameters as individual PHP variables and append them to the URL
        php_code = ""
        for key, values in query_params.items():
            var_name = self.camel_case(key)
            php_code += f"${var_name} = '{unquote(values[0])}';\n"
        
        php_code += f"\n$response = $this->get('{path}?{list(query_params.keys())[0]}='.${self.camel_case(list(query_params.keys())[0])}"
        for key in list(query_params.keys())[1:]:
            var_name = self.camel_case(key)
            php_code += f".'&{key}='.${var_name}"
        php_code += ");"

        # Display the PHP code in the output area
        self.query_output.delete("1.0", tk.END)
        self.query_output.insert(tk.END, php_code)
        self.root.clipboard_clear()
        self.root.clipboard_append(php_code)

    def parse_post_request(self, curl_command):
        start = curl_command.find("http")
        url = curl_command[start:].split()[0]
        parsed_url = urlparse(url)
        path = parsed_url.path

        # Extract data fields from the curl command using -F option
        data_segments = curl_command.split(" -F ")[1:]  # Extract data segments
        php_array = "$data = [\n"
        for segment in data_segments:
            key, value = segment.split("=", 1)
            key = key.strip().strip("'")
            value = value.strip().strip("'")
            php_array += f"    '{unquote(key)}' => '{unquote(value)}',\n"
        php_array = php_array.rstrip(",\n") + "\n];\n"

        php_code = php_array + f"\n$response = $this->post('{path}', $data);"

        # Display the PHP code in the output area
        self.query_output.delete("1.0", tk.END)
        self.query_output.insert(tk.END, php_code)
        self.root.clipboard_clear()
        self.root.clipboard_append(php_code)

    def toggle_php_code(self):
        if self.php_code_var.get():
            self.query_output.pack(padx=10, pady=(0, 10))
        else:
            self.query_output.pack_forget()

    def camel_case(self, text):
        parts = text.split('_')
        return parts[0] + ''.join(word.capitalize() for word in parts[1:])

    def parse_json_structure(self, data):
        if isinstance(data, dict):
            return {k: self.parse_json_structure(v) for k, v in data.items()}
        elif isinstance(data, list):
            if len(data) > 0 and isinstance(data[0], dict):
                return {'*': self.parse_json_structure(data[0])}
            else:
                return []
        else:
            return None

    def format_structure(self, structure, indent=0):
        indent_str = '    ' * indent
        if isinstance(structure, dict):
            formatted_items = []
            for key, value in structure.items():
                if isinstance(value, dict):
                    value_str = self.format_structure(value, indent + 1)
                    formatted_items.append(f"'{key}' => {value_str}")
                elif isinstance(value, list):
                    if value == []:
                        formatted_items.append(f"'{key}' => ['*']")
                    else:
                        formatted_items.append(f"'{key}' => [\n{indent_str}    '*' => {self.format_structure(value['*'], indent + 2)}\n{indent_str}]")
                else:
                    formatted_items.append(f"'{key}'")
            return "[\n" + ",\n".join(f"{indent_str}{item}" for item in formatted_items) + f"\n{indent_str}]"
        elif isinstance(structure, list):
            return "[]"
        else:
            return "[]"

    def toggle_json_format(self):
        if self.pretty_json_var.get():
            self.raw_json_output.delete("1.0", tk.END)
            self.raw_json_output.insert(tk.END, self.raw_json_output.pretty_json)
        else:
            self.raw_json_output.delete("1.0", tk.END)
            self.raw_json_output.insert(tk.END, self.raw_json_output.raw_json)

    def toggle_raw_json(self):
        if self.show_json_var.get():
            self.raw_json_output.pack(padx=10, pady=(0, 10))
        else:
            self.raw_json_output.pack_forget()

    def add_to_history(self, curl_command, raw_json, formatted_structure):
        self.history.append((curl_command, raw_json, formatted_structure))
        self.future.clear()  # Clear the future stack on new command

    def undo(self, event=None):
        if self.history:
            self.future.append(self.history.pop())
            self.load_state_from_history()

    def redo(self, event=None):
        if self.future:
            self.history.append(self.future.pop())
            self.load_state_from_history()

    def load_state_from_history(self):
        if self.history:
            curl_command, raw_json, formatted_structure = self.history[-1]
            self.curl_input.delete("1.0", tk.END)
            self.curl_input.insert(tk.END, curl_command)
            self.raw_json_output.delete("1.0", tk.END)
            self.raw_json_output.insert(tk.END, raw_json)
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, f"assertJsonStructure({formatted_structure})")

    def copy_output(self):
        output = self.output_text.get("1.0", tk.END).strip()
        if output:
            self.root.clipboard_clear()
            self.root.clipboard_append(output)

        else:
            messagebox.showwarning("Warning", "No output to copy.")

    def copy_query_output(self):
        query_output = self.query_output.get("1.0", tk.END).strip()
        if query_output:
            self.root.clipboard_clear()
            self.root.clipboard_append(query_output)
            messagebox.showinfo("Copied", "PHP code copied to clipboard.")
        else:
            messagebox.showwarning("Warning", "No PHP code to copy.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CurlJSONFormatterApp(root)
    root.mainloop()
