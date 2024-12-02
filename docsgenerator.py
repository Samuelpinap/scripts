import re
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
import json
import os
class TagManager:
    """Manages tag types dynamically and saves them to a file."""
    def __init__(self, filename="tags.json"):
        self.filename = filename
        self.tag_types = self.load_tags()

    def load_tags(self):
        """Load tags from a file."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, "r") as file:
                    return json.load(file)
            except (json.JSONDecodeError, IOError):
                pass
        # Default tags if file is missing or corrupted
        return [
            {"name": "Backoffice", "route_prefix": "/api/v1/backoffice"},
            {"name": "Portal", "route_prefix": "/api/v1/portal"}
        ]

    def save_tags(self):
        """Save tags to a file."""
        try:
            with open(self.filename, "w") as file:
                json.dump(self.tag_types, file, indent=4)
        except IOError as e:
            messagebox.showerror("Error", f"Failed to save tags: {e}")

    def add_tag(self, new_tag, route_prefix=""):
        """Add a new tag with an optional route prefix."""
        # Check if tag already exists
        for tag in self.tag_types:
            if tag['name'] == new_tag:
                return False
        
        # Add new tag
        self.tag_types.append({
            "name": new_tag,
            "route_prefix": route_prefix.strip() or f"/api/v1/{new_tag.lower()}"
        })
        self.save_tags()
        return True

    def delete_tag(self, tag):
        """Delete a tag from the list."""
        self.tag_types = [t for t in self.tag_types if t['name'] != tag]
        self.save_tags()

    def get_route_prefix(self, tag_name):
        """Get route prefix for a given tag name."""
        for tag in self.tag_types:
            if tag['name'] == tag_name:
                return tag.get('route_prefix', '')
        return ''



# Initialize tag manager
tag_manager = TagManager()


def update_tag_list():
    """Update the tag list with delete buttons."""
    for widget in tag_list_frame.winfo_children():
        widget.destroy()

    for tag in tag_manager.tag_types:
        frame = tk.Frame(tag_list_frame)
        frame.pack(fill="x", pady=2)

        tag_label = tk.Label(frame, text=tag, anchor="w")
        tag_label.pack(side="left", padx=5)

        delete_button = tk.Button(
            frame, text="X", fg="red", command=lambda t=tag: delete_tag(t)
        )
        delete_button.pack(side="right", padx=5)


def delete_tag(tag):
    """Delete a tag from the list."""
    tag_manager.delete_tag(tag)
    update_tag_dropdown()
    update_tag_list()

def update_tag_dropdown():
    """Update the tag dropdown with the latest tag types."""
    tag_dropdown['values'] = [tag['name'] for tag in tag_manager.tag_types] + ["Add"]

def handle_tag_selection(event):
    """Handle the selection of a tag in the dropdown."""
    selected = tag_type_var.get()
    if selected == "Add":
        add_tag_popup()
    else:
        # Automatically populate route prefix when a tag is selected
        route_prefix = tag_manager.get_route_prefix(selected)
        route_prefix_entry.delete(0, tk.END)
        route_prefix_entry.insert(0, route_prefix)

def add_tag_popup():
    """Show a popup window for adding a new tag."""
    popup = tk.Toplevel(root)
    popup.title("Add New Tag")

    # Tag name input
    tag_label = tk.Label(popup, text="Enter new tag:")
    tag_label.pack(pady=5)
    tag_entry = tk.Entry(popup)
    tag_entry.pack(pady=5)

    # Route prefix input
    route_prefix_label = tk.Label(popup, text="Route Prefix (optional):")
    route_prefix_label.pack(pady=5)
    route_prefix_entry = tk.Entry(popup)
    route_prefix_entry.pack(pady=5)

    def save_new_tag():
        new_tag = tag_entry.get().strip()
        route_prefix = route_prefix_entry.get().strip()
        
        if tag_manager.add_tag(new_tag, route_prefix):
            messagebox.showinfo("Success", f"Tag '{new_tag}' added successfully.")
            update_tag_dropdown()
            update_tag_list()
        else:
            messagebox.showwarning("Duplicate", f"Tag '{new_tag}' already exists.")
        popup.destroy()

    save_button = tk.Button(popup, text="Save", command=save_new_tag)
    save_button.pack(pady=10)


def extract_details_from_controller(controller_code):
    """
    Extract fields, types, and requirements from a Laravel controller.
    """
    try:
        # Extract validations from $this->validate() or Validator::make()
        validation_matches = re.findall(
            r"'([a-zA-Z_]+)'\s*=>\s*'(\w+)'", controller_code
        )
        validations = {match[0]: match[1] for match in validation_matches}

        # Extract fields from $request-> assignments
        field_matches = re.findall(
            r"\$[a-zA-Z_]+->([a-zA-Z_]+)\s*=\s*\$request->([a-zA-Z_]+)", controller_code
        )
        fields = {field[1] for field in field_matches}

        status, message = '', ''
        status_match = re.search(r"'status'\s*=>\s*'(\w+)'", controller_code)
        message_match = re.search(r"'message'\s*=>\s*'([^']+)'", controller_code)
        if status_match:
            status = status_match.group(1)

        if message_match:
            message = message_match.group(1)
        # Extract route parameter name
        param_match = re.search(r"\(Request \$\w+, \w+ (\$\w+)", controller_code)
        if not param_match:
            param_match = re.search(r"\(\w+ (\$\w+)", controller_code)
        route_param = param_match.group(1).removeprefix("$") if param_match else "id"

        # Combine validations and fields, infer types and required status
        all_fields = {}
        for field in fields:
            field_type = (
                "integer"
                if "id" in field.lower() or validations.get(field) == "integer"
                else "string"
            )
            is_required = field in validations
            all_fields[field] = {"type": field_type, "required": is_required}

        # Extract query parameters for index method
        query_params_matches = re.findall(r"\$request->([a-zA-Z_]+)", controller_code)
        for param in query_params_matches:
            if param not in all_fields:
                all_fields[param] = {"type": "string", "required": False}
        print(all_fields)
        return all_fields, route_param, status, message
    except Exception as e:
        raise ValueError(f"Error extracting details from controller: {e}")


def generate_example(field_name, field_type, module_name):
    """
    Generate dynamic examples based on field type and module name.
    """
    if field_type == "integer":
        return 1
    return f"{module_name.capitalize()} {field_name.replace('_', ' ').capitalize()}"


def generate_swagger_doc(
    details,
    route_param,
    module_name="Example",
    route_prefix="/api/v1",
    operation_type="store",
    status = '', 
    message= ''
):
    """
    Generate Swagger documentation based on the operation type.
    """
    try:
        required_fields = [
            field for field, props in details.items() if props["required"]
        ]
        properties = "\n".join(
            f" * @OA\\Property(property=\"{field}\", type=\"{props['type']}\", "
            f"description=\"{field.replace('_', ' ').capitalize()}\", "
            f"example=\"{generate_example(field, props['type'], module_name)}\"),"
            for field, props in details.items()
        )
        # Set up dynamic descriptions and tags
        tag_name = f"{module_name.title()} {tag_type_var.get()}"
        description = f"{operation_type.capitalize()} {module_name.title()}"
        operation_id = f"{operation_type}_{module_name.replace(' ', '_').lower()}"
        route = f"{route_prefix}/{module_name.lower()}"
        comillas = '"'
        query_parameters = ""
        print(query_parameters)
        correctresponse = (
            f" *     @OA\\Response(\n"
            f" *        response={'201' if operation_type.lower()=='store' else '200'},\n"
            f' *        description="Successful {operation_type}",\n'
            f' *        @OA\\JsonContent(@OA\\Property(property="data", type="object", example="[...]")\n'
            f" *        )\n"
            f" *     ),\n"
        )
        notfoundresponse = ""
        if operation_type == "update":
            route += f"/{{{route_param}}}/update"
            path_parameter = (
                " *     @OA\\Parameter(\n"
                f" *         name={comillas+route_param+comillas},\n"
                ' *         in="path",\n'
                ' *         description="ID of the resource to update",\n'
                " *         required=true,\n"
                ' *         @OA\\Schema(type="integer", example=1)\n'
                " *     ),\n"
            )
            notfoundresponse = (
                "*     @OA\Response(\n"
                "*        response=404,\n"
                '*        description="Error recurso no encontrado",\n'
                '*        @OA\JsonContent(@OA\Property(property="status", type="string", example="error"),\n'
                '*                     @OA\Property(property="message", type="string", example="Recurso no encontrado"),\n'
                "*        )\n"
                "*     ),\n"
            )
            operation_method = "POST"
            request_body = (
                f" *     @OA\\RequestBody(\n"
                f" *        required=true,\n"
                f' *        @OA\\MediaType(mediaType="multipart/form-data",\n'
                f" *           @OA\\Schema(\n"
                f" *              required={{ {', '.join(f'{comillas+f+comillas}' for f in required_fields)} }},\n"
                f" *              {properties}\n"
                f" *           )\n"
                f" *        ),\n"
                f" *     ),\n"
            )
        elif operation_type == "show":
            route += f"/{{{route_param}}}/show"
            path_parameter = (
                " *     @OA\\Parameter(\n"
                f" *         name={comillas+route_param+comillas},\n"
                ' *         in="path",\n'
                ' *         description="ID of the resource to show",\n'
                " *         required=true,\n"
                ' *         @OA\\Schema(type="integer", example=1)\n'
                " *     ),\n"
            )
            notfoundresponse = (
                "*     @OA\Response(\n"
                "*        response=404,\n"
                '*        description="Error recurso no encontrado",\n'
                '*        @OA\JsonContent(@OA\Property(property="status", type="string", example="error"),\n'
                '*                     @OA\Property(property="message", type="string", example="Recurso no encontrado"),\n'
                "*        )\n"
                "*     ),\n"
            )
            operation_method = "GET"
            request_body = ""
        elif operation_type == "delete":
            route += f"/{{{route_param}}}/delete"
            statusResponse =  'successful' if status == '' else status
            responseMessage ='Recurso borrado' if message == '' else message
            path_parameter = (
                " *     @OA\\Parameter(\n"
                f" *         name={comillas+route_param+comillas},\n"
                ' *         in="path",\n'
                ' *         description="ID of the resource to delete",\n'
                " *         required=true,\n"
                ' *         @OA\\Schema(type="integer", example=1)\n'
                " *     ),\n"
            )
            notfoundresponse = (
                "*     @OA\Response(\n"
                "*        response=404,\n"
                '*        description="Error recurso no encontrado",\n'
                '*        @OA\JsonContent(@OA\Property(property="status", type="string", example="error"),\n'
                '*                     @OA\Property(property="message", type="string", example="Recurso no encontrado"),\n'
                "*        )\n"
                "*     ),\n"
            )
            correctresponse = (
                "*     @OA\Response(\n"
                "*        response=200,\n"
                '*        description="Successful Deleted",\n'
                f'*        @OA\JsonContent(@OA\Property(property="status", type="string", example="{statusResponse}"),\n'
                f'*                     @OA\Property(property="message", type="string", example="{responseMessage}"),\n'
                "*         )\n"
                "*     ),\n"
            )
            operation_method = "DELETE"
            request_body = ""
        elif operation_type == "index":
            route += ""
            path_parameter = ""
            query_parameters = "\n".join(
                f" *     @OA\\Parameter(\n"
                f' *         name="{field}",\n'
                ' *         in="query",\n'
                f" *         description=\"{field.replace('_', ' ').capitalize()}\",\n"
                " *         required=false,\n"
                f" *         @OA\\Schema(type=\"{props['type']}\", example=\"{generate_example(field, props['type'], module_name)}\")\n"
                " *     ),"
                for field, props in details.items()
            )
            request_body = ""
            operation_method = "GET"
        else:
            operation_method = "POST"
            path_parameter = ""
            query_parameters = ""
            request_body = (
                f" *     @OA\\RequestBody(\n"
                f" *        required=true,\n"
                f' *        @OA\\MediaType(mediaType="multipart/form-data",\n'
                f" *           @OA\\Schema(\n"
                f" *              required={{ {', '.join(f'{comillas+f+comillas}' for f in required_fields)} }},\n"
                f" *              {properties}\n"
                f" *           )\n"
                f" *        ),\n"
                f" *     ),\n"
            )

        # Build required and optional properties

        corcheteI = "{"
        corcheteF = "}"
        # Construct the Swagger documentation
        swagger_doc = (
            "/**\n"
            f" * @OA\\{operation_method}(\n"
            f' *     tags={{"{tag_name}"}},\n'
            f' *     path="{route}",\n'
            f' *     description="{description}",\n'
            f' *     security={{{corcheteI}"token": {{}}{corcheteF}}},\n'
            f' *     operationId="{operation_id}",\n'
            f"{path_parameter}"
            f"{query_parameters}"
            f"{request_body}"
            f"{correctresponse}"
            f" *     @OA\\Response(\n"
            f" *        response=401,\n"
            f' *        description="Bad Request",\n'
            f" *        @OA\\JsonContent(\n"
            f' *           @OA\\Property(property="message", type="string", example="Unauthenticated")\n'
            f" *        )\n"
            f" *     ),\n"
            f"{notfoundresponse}"
            f" * )\n"
            f" */"
        )
        return swagger_doc
    except Exception as e:
        raise ValueError(f"Error generating Swagger doc: {e}")


def generate_documentation():
    """
    Main function to generate documentation and display it in the UI.
    """
    try:
        controller_input = controller_text.get("1.0", tk.END).strip()
        route_prefix = route_prefix_entry.get().strip()
        module_name = module_name_entry.get().strip() or "Example"
        operation_type = operation_type_var.get()

        if not controller_input:
            raise ValueError("Controller input is required.")

        details, route_param, status, message = extract_details_from_controller(controller_input)
        swagger_doc = generate_swagger_doc(
            details, route_param, module_name, route_prefix, operation_type, status, message
        )

        output_text.delete("1.0", tk.END)
        output_text.insert(tk.END, swagger_doc)
    except Exception as e:
        messagebox.showerror("Error", str(e))


# UI Setup
root = tk.Tk()
root.title("Laravel Swagger Documentation Generator")
tag_frame = tk.Frame(root)
tag_frame.pack(pady=10, padx=10, fill="x")
# Input Frame
input_frame = tk.Frame(root)
input_frame.pack(pady=10, padx=10, fill="x")

# Create a BooleanVar to hold the state of the checkbox
boolean_var = tk.BooleanVar(value=False)

# Function to update the visibility of the tag list
def update_tag_list_visibility():
    if boolean_var.get():
        tag_list_label.pack(anchor="w", padx=10)
        tag_list_frame.pack(pady=10, padx=10, fill="x")
        update_tag_list()
    else:
        tag_list_label.pack_forget()
        tag_list_frame.pack_forget()

tag_label = tk.Label(tag_frame, text="Tag Type:")
tag_label.pack(anchor="w")
tag_type_var = tk.StringVar(value="Backoffice")
tag_dropdown = ttk.Combobox(tag_frame, textvariable=tag_type_var, state="readonly")
update_tag_dropdown()
tag_dropdown.bind("<<ComboboxSelected>>", handle_tag_selection)
tag_dropdown.pack(side="left")

# Create a Checkbutton and place it to the right of the dropdown
boolean_checkbutton = tk.Checkbutton(tag_frame, text="Delete", variable=boolean_var, command=update_tag_list_visibility)
boolean_checkbutton.pack(side="right")



# # Tag List Frame
# if boolean_var.get():
#     tag_list_label = tk.Label(root, text="Tag List:")
#     tag_list_label.pack(anchor="w", padx=10)

#     tag_list_frame = tk.Frame(root)
#     tag_list_frame.pack(pady=10, padx=10, fill="x")
#     update_tag_list()


# Tag List Frame
tag_list_label = tk.Label(root, text="Tag List:")
tag_list_label.pack(anchor="w", padx=10)

tag_list_frame = tk.Frame(root)
tag_list_frame.pack(pady=10, padx=10, fill="x")
update_tag_list()

# Initially update the visibility based on the boolean variable
update_tag_list_visibility()
controller_label = tk.Label(input_frame, text="Controller Code:")
controller_label.pack(anchor="w")

controller_text = ScrolledText(input_frame, height=15)
controller_text.pack(fill="x")

route_prefix_label = tk.Label(input_frame, text="Route Prefix (optional):")
route_prefix_label.pack(anchor="w")

route_prefix_entry = tk.Entry(input_frame)
route_prefix_entry.pack(fill="x")

module_name_label = tk.Label(input_frame, text="Module Name (optional):")
module_name_label.pack(anchor="w")

module_name_entry = tk.Entry(input_frame)
module_name_entry.pack(fill="x")

# Dropdown for operation type
operation_type_label = tk.Label(input_frame, text="Operation Type:")
operation_type_label.pack(anchor="w")

operation_type_var = tk.StringVar(value="store")
operation_type_dropdown = ttk.Combobox(
    input_frame, textvariable=operation_type_var, state="readonly"
)
operation_type_dropdown["values"] = ["store", "update", "index", "show", "delete"]
operation_type_dropdown.pack(fill="x")



# Buttons
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

generate_button = tk.Button(
    button_frame, text="Generate Documentation", command=generate_documentation
)
generate_button.pack()

# Output Frame
output_frame = tk.Frame(root)
output_frame.pack(pady=10, padx=10, fill="x")

output_label = tk.Label(output_frame, text="Generated Documentation:")
output_label.pack(anchor="w")

output_text = ScrolledText(output_frame, height=20)
output_text.pack(fill="x")

# Run UI
root.mainloop()
