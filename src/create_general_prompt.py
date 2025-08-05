import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

class InfoInputApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Input Information Form")

        self.entries = []

        self.setup_interface()

    def setup_interface(self):
        # Frame for number of entries
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=10)

        ttk.Label(control_frame, text="Nombre de champs :").pack(side=tk.LEFT, padx=5)
        self.num_fields_var = tk.IntVar(value=4)
        self.spinbox = ttk.Spinbox(control_frame, from_=1, to=20, width=5, textvariable=self.num_fields_var)
        self.spinbox.pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Générer les champs", command=self.generate_fields).pack(side=tk.LEFT, padx=10)

        # Canvas for scrollable fields
        self.canvas = tk.Canvas(self.root)
        self.scroll_y = tk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.form_frame = ttk.Frame(self.canvas)

        self.form_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scroll_y.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll_y.pack(side="right", fill="y")

        # Submit button
        ttk.Button(self.root, text="Afficher le dictionnaire", command=self.show_output).pack(pady=10)

        # Output
        self.output_box = scrolledtext.ScrolledText(self.root, height=10)
        self.output_box.pack(padx=10, pady=5, fill="both", expand=True)

    def generate_fields(self):
        # Clear current entries
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        self.entries = []

        n = self.num_fields_var.get()
        for i in range(n):
            field_frame = ttk.LabelFrame(self.form_frame, text=f"Champ {i+1}")
            field_frame.pack(fill="x", padx=10, pady=5)

            label_entry = self.create_labeled_entry(field_frame, "Label")
            desc_entry = self.create_labeled_entry(field_frame, "Description")
            example_entry = self.create_labeled_entry(field_frame, "Exemple")

            self.entries.append({
                "label": label_entry,
                "description": desc_entry,
                "exemple": example_entry
            })

    def create_labeled_entry(self, parent, label_text):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=2)
        ttk.Label(frame, text=label_text + " :", width=15).pack(side=tk.LEFT)
        entry = ttk.Entry(frame)
        entry.pack(side=tk.LEFT, fill="x", expand=True)
        return entry

    def show_output(self):
        output = []
        for entry_set in self.entries:
            label = entry_set["label"].get().strip()
            description = entry_set["description"].get().strip()
            exemple = entry_set["exemple"].get().strip()

            if not label or not description:
                messagebox.showwarning("Champs manquants", "Tous les champs doivent être remplis.")
                return

            # Try to cast example to int if possible
            try:
                exemple_val = int(exemple)
            except ValueError:
                exemple_val = exemple

            output.append({
                "label": label,
                "description": description,
                "exemple": exemple_val
            })

        # Display result
        self.output_box.delete("1.0", tk.END)
        self.output_box.insert(tk.END, f"input_information = {output}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InfoInputApp(root)
    root.mainloop()

# input_information = [{"label":"Nom", "description":"Le nom de la personne qui demande la commande", "exemple":"Dupont"},
#                       {"label":"Prénom", "description":"Le prénom de la personne qui commande", "exemple":"Antoine"},
#                       {"label":"Numéro de commande", "description":"Numéro de commande situé en haut du document a coté de l'intitulé 'commande'", "exemple":10456},
#                       {"label":"Date", "description": "Date à laquelle la commande a été faite","exemple":"10/07/2025"}]

# # create the prompt
# general_prompt = ""

# # introduction of the prompt
# intro_prompt = """Vous êtes une IA spécialisée dans l'extraction d'informations à partir de documents rédigés en français. Votre tâche est de transformer un document textuel fourni en entrée en un objet JSON structuré, en extrayant des informations spécifiques selon les règles et la structure définies ci-dessous. Suivez strictement les instructions pour garantir une sortie JSON valide et cohérente avec les exemples fournis.\n
# """

# # structure of the output
# table_extract = ""
# for champ in input_information:
#     table_extract += f"| `{champ['label']}`  | {champ['description']}  |\n"

# struct_prompt = f"""
# ## Instructions pour l'extraction des données

# ### Entrée : 

# Vous recevrez un document textuel.

# ### Sortie : Générez un objet JSON avec exactement les champs suivants, dans l'ordre indiqué :

# | Clé               | Description                           |
# | ----------------- | ------------------------------------- |
# {table_extract}

# ## Règles d'extraction :

# - Extrayez les informations textuelles exactement telles qu'elles apparaissent dans le document, sans modification de la casse ou des accents.
# - Si une information est absente, laissez le champ correspondant vide ("") pour les champs textuels ou None pour les valeurs numériques.
# - Ignorez toute information non pertinente pour les champs demandés.\n
# """

# # demonstrations
# demo_prompt = """
# ```json
# {
# """

# for champ in input_information:
#     demo_prompt += f"  '{champ['label']}' : '{champ['exemple']}',\n"

# demo_prompt += "}\n```"

# format_prompt = f"""
# ## Format de sortie :

# - La sortie doit être un objet JSON valide, contenant uniquement les champs spécifiés.
# - Assurez-vous que les valeurs textuelles respectent la casse, les accents et la ponctuation du texte original.
# - Les valeurs numériques ne doivent pas inclure de guillemets.

# ### Exemple de sortie :

# {demo_prompt}

# ## Contraintes supplémentaires :

# Ne modifiez pas les valeurs extraites.
# Ne faites pas d'hypothèses ou n'inventez pas de données pour les champs manquants.
# Ne générez pas de champs supplémentaires ou différents de ceux spécifiés.
# Assurez-vous que le JSON est syntaxiquement correct et cohérent avec les exemples fournis.


# Voici le texte à traiter :
# """

# # merge every prompt and save

# general_prompt = intro_prompt + struct_prompt + format_prompt
# with open("../prompt/general_prompt_extraction.txt", "w") as f:
#     f.write(general_prompt)