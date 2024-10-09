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
        self.show_formatted_structure = tk.BooleanVar(value=True)

        self.setup_ui()

        # Bindings for undo and redo on macOS
        self.root.bind('<Command-z>', self.undo)
        self.root.bind('<Command-Shift-Z>', self.redo)

    def setup_ui(self):
        self.root.title("Curl JSON Formatter")
        self.root.geometry("1000x1000")
        self.root.resizable(True, True)
        
         # Prefix input field
        prefix_frame = tk.Frame(self.root)
        prefix_frame.pack(fill=tk.X, padx=10, pady=10)
        prefix_label = tk.Label(prefix_frame, text="Prefix:")
        prefix_label.pack(side=tk.LEFT)
        self.prefix_input = tk.Entry(prefix_frame)
        self.prefix_input.pack(side=tk.RIGHT)
        self.prefix_input.insert(0, "api/v1")  # Default value


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
        
          # Test type selector
        tk.Label(self.root, text="Select Test Type:").pack(pady=(10, 0))
        self.test_type = ttk.Combobox(self.root, values=["List", "Create", "Show", "Update"], state="readonly")
        self.test_type.current(0)  # Set default to List
        self.test_type.pack(pady=(0, 10))


        # Execute and Copy button
        self.execute_and_copy_button = tk.Button(self.root, text="Execute Curl & Copy", command=self.execute_and_copy_curl)
        self.execute_and_copy_button.pack(pady=(0, 10))

        # Clear Curl Field button
        self.clear_curl_button = tk.Button(self.root, text="Clear Curl Field", command=self.clear_curl_field)
        self.clear_curl_button.pack(pady=(0, 10))

        # Extract Variables from CURL button
        self.extract_button = tk.Button(self.root, text="Extract Variables from CURL", command=self.extract_variables_from_curl)
        self.extract_button.pack(pady=(0, 10))

        self.formatted_structure_checkbox = tk.Checkbutton(
            self.root, 
            text="Show Formatted Structure", 
            variable=self.show_formatted_structure,
            command=self.toggle_formatted_structure
        )
        self.formatted_structure_checkbox.pack(pady=(10, 0))

        # Output label and text area for formatted structure
        self.formatted_structure_label = tk.Label(self.root, text="Formatted Structure:")
        self.formatted_structure_label.pack(pady=(10, 0))
        self.output_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=110, height=15)
        self.output_text.pack(padx=10, pady=(0, 10))

        # PHP Code Output area (initially hidden)
        self.query_output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=110, height=30)
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

    def toggle_formatted_structure(self):
        if self.show_formatted_structure.get():
            self.formatted_structure_label.pack(pady=(10, 0))
            self.output_text.pack(padx=10, pady=(0, 10))
        else:
            self.formatted_structure_label.pack_forget()
            self.output_text.pack_forget()
    def execute_curl(self):
        curl_command = self.curl_input.get("1.0", tk.END).strip()
        if not curl_command.startswith("curl"):
            messagebox.showerror("Error", "Please enter a valid curl command.")
            return
        
        try:
            # Extract method and URL
            method = "GET"
            url = ""
            data = []
            parts = curl_command.split()
            for i, part in enumerate(parts):
                if part.startswith("http"):
                    url = part
                elif part == "-X" and i + 1 < len(parts) and parts[i + 1] in ["POST", "GET"]:
                    method = parts[i + 1]
                elif part == "-F" and i + 1 < len(parts):
                    key_value = parts[i + 1].split("=", 1)
                    if len(key_value) == 2:
                        key, value = key_value
                        data.append("'{}'=>'{}'".format(key.strip("'"), value.strip("'")))

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

            # Parse and format the JSON structure
            json_data = json.loads(raw_json_string)
            structure = self.parse_json_structure(json_data)
            formatted_structure = self.format_structure(structure)
            
            if self.show_formatted_structure.get():
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert(tk.END, formatted_structure)
            # Generate and show the PHP tests
            path = self.extract_path_from_curl(curl_command)
            test_type = self.test_type.get()
            php_tests = self.generate_php_tests(path, formatted_structure, test_type, data, json_data)
            self.show_php_tests(php_tests)

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

        # Generate and display PHP test methods
        structure = self.output_text.get("1.0", tk.END).strip()  # Get the JSON structure
        php_tests = self.generate_php_tests(path, structure, query_params)
        self.show_php_tests(php_tests)


    def parse_post_request(self, curl_command):
        start = curl_command.find("http")
        url = curl_command[start:].split()[0]
        parsed_url = urlparse(url)
        path = parsed_url.path

        # Extract data fields from the curl command using -F option
        data_segments = curl_command.split(" -F ")[1:]  # Extract data segments
        php_array = "$data = [\n"
        data = []
        for segment in data_segments:
            key, value = segment.split("=", 1)
            key = key.strip().strip("'")
            value = value.strip().strip("'")
            php_array += f"    '{unquote(key)}' => '{unquote(value)}',\n"
            data.append(f"'{key}' => '{value}'")
        php_array = php_array.rstrip(",\n") + "\n];\n"

        php_code = php_array + f"\n$response = $this->post('{path}', $data);"

        # Display the PHP code in the output area
        self.query_output.delete("1.0", tk.END)
        self.query_output.insert(tk.END, php_code)
        self.root.clipboard_clear()
        self.root.clipboard_append(php_code)

        # Generate and display PHP test methods
        structure = self.output_text.get("1.0", tk.END).strip()  # Get the JSON structure
        php_tests = self.generate_php_tests(path, structure, self.test_type.get(), data, json.loads(self.raw_json_output.get("1.0", tk.END)))
        self.show_php_tests(php_tests)

    def show_php_tests(self, php_tests):
        # Show the PHP tests in the output area
        self.query_output.pack(padx=10, pady=(0, 10))
        self.query_output.delete("1.0", tk.END)
        self.query_output.insert(tk.END, php_tests)

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

    def camel_case(self, snake_str):
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    def generate_php_tests(self, path, structure, test_type, data=None, json_data=None):
        base_path = path.rstrip('/').split('/')[-1]
        
        if test_type == "List":
            return self.generate_list_tests(path, structure, json_data)
        elif test_type == "Create":
            return self.generate_create_tests(path, data, json_data)
        elif test_type == "Show":
            return self.generate_show_tests(path, json_data)
        elif test_type == "Update":
            return self.generate_update_tests(path, data, json_data)
        else:
            raise ValueError(f"Unknown test type: {test_type}")


    def generate_list_tests(self, path, structure, json_data, query_params=None):
        base_path = path.rstrip('/').replace('/', '_')
        structure = self.parse_json_structure(json_data)
        formatted_structure = self.format_structure(structure)
        # Test 1: Authenticated request test
        authenticated_test = f"""
        public function test_list_{base_path}_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));

            $response = $this->get('{path}');

            $response->assertStatus(200);
            $response->assertJsonStructure(
                 {formatted_structure});
            $this->assertNotTrue(count($response['data']) < 1, 'Response DATA is empty');
        }}
        """

        # Test 2: Invalid query parameter test
        invalid_param = list(query_params.keys())[0] if query_params else 'name'
        invalid_test = f"""
        public function test_list_{base_path}_invalid_{invalid_param}_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));

            $response = $this->get('{path}?{invalid_param}=invalid');

            $response->assertStatus(200);
            $response->assertJsonStructure([
                'data' => [
                ],
                'links' => [
                    'first',
                    'last',
                    'prev',
                    'next'
                ],
                'meta' => [
                    'current_page',
                    'from',
                    'last_page',
                    'links' => [
                        '*' => [
                            'url',
                            'label',
                            'active'
                        ]
                    ],
                    'path',
                    'per_page',
                    'to',
                    'total'
                ]
            ]);
            $this->assertTrue(count($response['data']) < 1, 'Response DATA is not empty');
        }}
        """

        # Test 3: Authenticated request without permission
        no_permission_test = f"""
        public function test_list_{base_path}_without_permission_authenticated()
        {{
            $this->$user = $user = User::where('email', 'user@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));

            $response = $this->get('{path}');

            $response->assertStatus(401);
            $response->assertJsonStructure([
                'status',
                'message'
            ]);
            $response->assertJsonPath('status', 'error');
            $response->assertJsonPath('message', 'Usuario no posee permisos');
        }}
        """

        # Test 4: Unauthenticated request test
        unauthenticated_test = f"""
        public function test_list_{base_path}_unauthenticated()
        {{
            $response = $this->get('{path}');

            $this->followRedirects($response)
                ->assertStatus(404)
                ->assertJsonStructure([
                    'message',
                    'status'
                ])->assertJsonPath('message', 'Ruta incorrecta o user no autenticado');
        }}
        """

        return (authenticated_test + invalid_test + no_permission_test + unauthenticated_test).replace("''", "'").replace("'_", "_").replace("_'","_")
    def generate_create_tests(self, path, data, json_data):
        base_path = path.rstrip('/').split('/')[-1]
        title_path = path.rstrip('/').replace('/', '_')
    
        data_str = "[\n            " + ",\n            ".join(data) + "\n        ,]"
    
        # Define generate_structure as a nested function
        def generate_structure(data, indent=3):
            if isinstance(data, dict):
                return {k: generate_structure(v) for k, v in data.items()}
            elif isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    return {'*': generate_structure(data[0])}
                else:
                    return []
            else:
                return None

        structure = self.parse_json_structure(json_data)
        formatted_structure = self.format_structure(structure)
        
        # Generate error messages for all fields
        error_assertions = "\n".join([f"            '{key.split('=')[0]}' => 'El campo {key.split('=')[0].replace('_', ' ')} es requerido.'" for key in data])
        json_path_assertions = "\n".join([f"            $response->assertJsonPath('data.{key.split('=>')[0]}', $data['{key.split('=>')[0]}']);" for key in data])
         
        # Test 1: Authenticated create test
        authenticated_test = f"""
        public function test_create_{title_path}_authenticated()
        {{
            $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));

            // Test data
            $data = {data_str};
            $response = $this->post('{path}', $data);

            // Assert status
            $response->assertStatus(201);

            // Assert JSON structure
            $response->assertJsonStructure({formatted_structure});

              // Dynamically assert JSON paths
            {json_path_assertions}

            // Assert database contains the created record
            $this->assertDatabaseHas('{base_path}s', {data_str});

            // Assert the response data is not empty
            $this->assertNotTrue(count($response['data']) < 1, 'Response DATA is empty');
        }}
        """
        # Test 2: Create without permission
        no_permission_test = f"""
        public function test_create_{title_path}_without_permission_authenticated()
        {{
            $user = User::where('email', 'user@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            $data = {data_str};
            $response = $this->post('{path}', $data);
            $response->assertStatus(401);
            $response->assertJsonStructure([
                'status',
                'message'
            ]);
            $response->assertJsonPath('status', 'error');
            $response->assertJsonPath('message', 'Usuario no posee permisos');
        }}
        """
        # Test 3: Create with missing info
        missing_info_test = f"""
        public function test_create_{title_path}_missing_info_authenticated()
        {{
            $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            $data = [];
            $response = $this->post('{path}', $data);
            $response->assertSessionHasErrors([
    {error_assertions}
            ]);
        }}
        """

        # Test 4: Unauthenticated create test
        unauthenticated_test = f"""
        public function test_create_{title_path}_unauthenticated()
        {{
            $data = {data_str};
            $response = $this->post('{path}', $data);
            $this->followRedirects($response)
                ->assertStatus(404)
                ->assertJsonStructure([
                    'message',
                    'status'
                ])->assertJsonPath('message', 'Ruta incorrecta o user no autenticado');
        }}
        """

        return (authenticated_test + no_permission_test + missing_info_test + unauthenticated_test).replace("''", "'").replace("'_", "_").replace("_'","_")

    def generate_show_tests(self, path, json_data):
        base_path = path.rstrip('/').split('/')[-1]
        title_path = path.rstrip('/').replace('/', '_')
        
        # Generate assertJsonStructure based on json_data
        def generate_structure(data, indent=3):
            if isinstance(data, dict):
                return {k: generate_structure(v) for k, v in data.items()}
            elif isinstance(data, list):
                if len(data) > 0 and isinstance(data[0], dict):
                    return {'*': generate_structure(data[0])}
                else:
                    return []
            else:
                return None

        # json_structure = generate_structure(json_data['data'])
        structure = self.parse_json_structure(json_data)
        formatted_structure = self.format_structure(structure)
        


        # Test 1: Authenticated show test
        authenticated_test = f"""
        public function test_show_{title_path}_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->first()->id;
            $response = $this->get('{path}/' . ${base_path}Id . '/show');
            $response->assertStatus(200);
            $response->assertJsonStructure({formatted_structure});
            $this->assertNotTrue(count($response['data'])<1,'Response DATA is empty');
        }}
        """

        # Test 2: Invalid ID test
        invalid_id_test = f"""
        public function test_show_{title_path}_invalid_id_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->last()->id+9999;
            $this->withoutExceptionHandling();
            $this->expectException(ModelNotFoundException::class);
            $response = $this->get('{path}/' . ${base_path}Id . '/show');
        }}
        """

        # Test 3: Without permission test
        no_permission_test = f"""
        public function test_show_{title_path}_without_permission_authenticated()
        {{
            $this->$user = $user = User::where('email', 'user@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->first()->id;
            $response = $this->get('{path}/' . ${base_path}Id . '/show');
            $response->assertStatus(401);
            $response->assertJsonStructure([
                'status',
                'message'
            ]);
            $response->assertJsonPath('status', 'error');
            $response->assertJsonPath('message', 'Usuario no posee permisos');
        }}
        """

        # Test 4: Unauthenticated test
        unauthenticated_test = f"""
        public function test_show_{title_path}_unauthenticated()
        {{
            ${base_path}Id = {base_path.capitalize()}::all()->first()->id;
            $response = $this->get('{path}/' . ${base_path}Id . '/show');
            $this->followRedirects($response)
                ->assertStatus(404)
                ->assertJsonStructure([
                    'message',
                    'status'
                ])->assertJsonPath('message', 'Ruta incorrecta o user no autenticado');
        }}
        """

        return (authenticated_test + invalid_id_test + no_permission_test + unauthenticated_test).replace("''", "'").replace("'_", "_").replace("_'","_")

    def generate_update_tests(self, path, data, json_data):
        base_path = path.rstrip('/').split('/')[-1] # Get the base path (e.g., 'procedures')
        title_path = path.replace(self.prefix_input.get(), "").rstrip('/').replace('/', '_')
        data_str = "[\n            " + ",\n            ".join(data) + "\n        ]"
        
        structure = self.parse_json_structure(json_data)
        formatted_structure = self.format_structure(structure)
        
        # Generate error messages for all fields
        error_assertions = "\n".join([f"            '{key.split('=')[0]}' => 'El campo {key.split('=')[0].replace('_', ' ')} es requerido.'" for key in data])
        json_path_assertions = "\n".join([f"            ->assertJsonPath('data.{key.split('=>')[0]}', $data['{key.split('=>')[0]}'])" for key in data])
        
        # Test 1: Authenticated update test
        authenticated_test = f"""
        public function test_update_{title_path}_by_id_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->last()->id;
            $data = {data_str};
            $response = $this->post('{path}/' . ${base_path}Id . '/update', $data);
            $response->assertStatus(200);
            $response->assertJsonStructure({formatted_structure})
            {json_path_assertions};
            $this->assertDatabaseHas('{base_path}', {data_str});
            $this->assertNotTrue(count($response['data'])<1,'Response DATA is empty');
        }}
        """

        # Test 2: Update without permission
        no_permission_test = f"""
        public function test_update_{title_path}_by_id_without_permission_authenticated()
        {{
            $this->$user = $user = User::where('email', 'user@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->last()->id;
            $data = {data_str};
            $response = $this->post('{path}/' . ${base_path}Id . '/update', $data);
            $response->assertStatus(401);
            $response->assertJsonStructure([
                'status',
                'message'
            ]);
            $response->assertJsonPath('status', 'error');
            $response->assertJsonPath('message', 'Usuario no posee permisos');
        }}
        """

        # Test 3: Update with missing info
        missing_info_test = f"""
        public function test_update_{title_path}_by_id_missing_info_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->last()->id;
            $data = [];
            $response = $this->post('{path}/' . ${base_path}Id . '/update', $data);
            $response->assertSessionHasErrors([
    {error_assertions}
            ]);
        }}
        """

        # Test 4: Update with invalid ID
        invalid_id_test = f"""
        public function test_update_{title_path}_by_invalid_id_authenticated()
        {{
            $this->$user = $user = User::where('email', 'admin@pruebas.com')->first();
            $this->actingAs(Passport::actingAs($user));
            ${base_path}Id = {base_path.capitalize()}::all()->last()->id+999;
            $data = {data_str};
            $this->withoutExceptionHandling();
            $this->expectException(ModelNotFoundException::class);
            $response = $this->post('{path}/' . ${base_path}Id . '/update', $data);
        }}
        """

        # Test 5: Unauthenticated update test
        unauthenticated_test = f"""
        public function test_update_{title_path}_by_id_unauthenticated()
        {{
            $data = {data_str};
            $response = $this->post('{path}/1/update', $data);
            $this->followRedirects($response)
                ->assertStatus(404)
                ->assertJsonStructure([
                    'message',
                    'status'
                ])->assertJsonPath('message', 'Ruta incorrecta o user no autenticado');
        }}
        """

        return (authenticated_test + no_permission_test + missing_info_test + invalid_id_test + unauthenticated_test).replace("''", "'").replace("'_", "_").replace("_'","_")
    def toggle_raw_json(self):
        if self.show_json_var.get():
            self.raw_json_output.pack(padx=10, pady=(0, 10))
        else:
            self.raw_json_output.pack_forget()

    def toggle_json_format(self):
        if self.pretty_json_var.get():
            # Convert raw JSON to pretty JSON
            raw_json = self.raw_json_output.get("1.0", tk.END).strip()
            try:
                pretty_json = json.dumps(json.loads(raw_json), indent=4)
                self.raw_json_output.delete("1.0", tk.END)
                self.raw_json_output.insert(tk.END, pretty_json)
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON format.")
        else:
            # Convert pretty JSON back to raw JSON
            pretty_json = self.raw_json_output.get("1.0", tk.END).strip()
            try:
                raw_json = json.dumps(json.loads(pretty_json))
                self.raw_json_output.delete("1.0", tk.END)
                self.raw_json_output.insert(tk.END, raw_json)
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Invalid JSON format.")

    def extract_path_from_curl(self, curl_command):
        start = curl_command.find("http")
        url = curl_command[start:].split()[0]
        parsed_url = urlparse(url)
        path = parsed_url.path
        
        # Remove the ID and 'show' from the path for the show method
        if path.endswith("/show") or path.endswith("/show'"):
            parts = path.split('/')
            return '/'.join(parts[:-2])  # Remove the last two parts (ID and 'show')
         
        if path.endswith("/update") or path.endswith("/update'"):
            parts = path.split('/')
            return '/'.join(parts[:-2])  
        return path

    def undo(self, event=None):
        if self.history:
            self.future.append(self.curl_input.get("1.0", tk.END))
            last_state = self.history.pop()
            self.curl_input.delete("1.0", tk.END)
            self.curl_input.insert(tk.END, last_state)

    def redo(self, event=None):
        if self.future:
            self.history.append(self.curl_input.get("1.0", tk.END))
            next_state = self.future.pop()
            self.curl_input.delete("1.0", tk.END)
            self.curl_input.insert(tk.END, next_state)


# Create the application window and run the app
root = tk.Tk()
app = CurlJSONFormatterApp(root)
root.mainloop()