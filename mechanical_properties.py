import sqlite3

class MaterialsDatabase:
    DEFUALT_MATERIAL_CATEGORIES = ['Metal', 'Plastic', 'Glass', 'Other']

    def __init__(self, filename):
        self.__CONN = sqlite3.connect(f'file:{filename}?mode=rw', uri=True)
        self.__CUR = self.__CONN.cursor()
        self.__CUR.row_factory = sqlite3.Row
        self.__CUR.execute("PRAGMA foreign_keys=ON")


    def __add_material(self, name, category):
        try:
            self.__CUR.execute("INSERT INTO materials(name, material_category) VALUES (?, ?)", (name, category))
            self.__CONN.commit()
        except sqlite3.IntegrityError:
            print('A material with that name already exists, please update that material instead...')

    def __add_mechanical_properties(self, material, properties):
        self.__CUR.execute("INSERT INTO mechanical_properties(material, density, modulus_of_elasticity, modulus_of_rigidity, yield_strength, ultimate_tensile_strength, percent_elongation) VALUES (?,?,?,?,?,?,?)", (material, *properties))
        self.__CONN.commit()
    
    def add_entry(self, name, category, properties):
        self.__add_material(name, category)
        self.__add_mechanical_properties(name, properties)
    
    def update_material(self, material_id, column, value):
        self.__CUR.execute(f'''
            UPDATE mechanical_properties
            SET
                {column} = ?
            WHERE
                material_id = ? ;''', (value, material_id))
        self.__CONN.commit()
        return self.__CUR.rowcount == 1

    def get_all_entries(self, order_by='material', descending=False):
        results = self.__CUR.execute(f'''
        SELECT
            *
        FROM
	        properties
         ORDER BY
            {order_by + f'{" ASC " if not descending else " DESC "}'} ;''')
        return results.fetchall()
    
    def get_entry_by_material(self, material):
        results = self.__CUR.execute(f'''
        SELECT
            *
        FROM
	        properties
        WHERE
            material = ?;''', (material,))
        return results.fetchall()
    
    def delete_material(self, name):
        self.__CUR.execute('''
            DELETE FROM materials
            WHERE name = ?;''', (name,))
        
        if self.__CUR.rowcount == 1:
            self.__CONN.commit()
            return True
        else:
            return False

    @staticmethod
    def create_database(filename):
        conn = sqlite3.connect(filename)
        cur = conn.cursor()

        cur.execute('''
            CREATE TABLE materials(
                name TEXT UNIQUE NOT NULL PRIMARY KEY,
                material_category TEXT NOT NULL,
                FOREIGN KEY(material_category) REFERENCES material_categories(name));''')

        cur.execute('''
            CREATE TABLE material_categories(
                material_category_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
                name TEXT NOT NULL UNIQUE
				);''')

        cur.execute('''
            CREATE TABLE mechanical_properties(
                material TEXT UNIQUE NOT NULL PRIMARY KEY,
                density INTEGER,
                modulus_of_elasticity INTEGER,
                modulus_of_rigidity INTEGER,
                yield_strength INTEGER,
                ultimate_tensile_strength INTEGER,
                percent_elongation INTEGER,
                FOREIGN KEY(material) REFERENCES materials(name) ON DELETE CASCADE);''')
                

        for material_category in MaterialsDatabase.DEFUALT_MATERIAL_CATEGORIES:
            cur.execute('''
                INSERT INTO material_categories(name) VALUES (?); ''', (material_category,))

        cur.execute('''
            CREATE VIEW properties
            AS
            SELECT
                materials.name AS material,
                material_categories.name AS category,
                density,
                modulus_of_elasticity,
                modulus_of_rigidity,
                yield_strength,
                ultimate_tensile_strength,
                percent_elongation
            FROM
                materials
            INNER JOIN material_categories ON (material_category = material_categories.name)
            INNER JOIN mechanical_properties ON(materials.name = material);''')

        conn.commit()


    def get_material_categories(self):
        results = self.__CUR.execute('''
        SELECT
            name
        FROM
	        material_categories
         ORDER BY
            material_category_id ASC;''')
        return results.fetchall()

        

class MaterialsDatabaseEditor:
    COLUMN_DISPLAYS = {'material':'Material', 'category':'Category', 'density':'ρ(kg/m³)', 'modulus_of_elasticity':'E(GPa)', 'modulus_of_rigidity':'G(GPa)', 'yield_strength':'σy(MPa)', 'ultimate_tensile_strength':'σult(MPa)', 'percent_elongation':r'%EL'}
    COLUMN_SPACING = 11

    def __init__(self, filename):
        self.database = MaterialsDatabase(filename)

    def prompt_name(self):
        name = input('\tMaterial Name: ')
        return name
            
    def prompt_properties(self):
        try:
            density = int(input('\tDensity (kg/m³): '))
            modulus_of_elasticity = int(input('\tModulus of Elasticity (GPa): '))
            modulus_of_rigidity = int(input('\tModulus of Rigidity (GPa): '))
            yeild_strength = int(input('\tYield Strength (MPa): '))
            ultimate_tensile_strength = int(input('\tUltimate Tensile Strength (MPa): '))
            percent_elongation = int(input('\tPercent Elongation (%): '))
            
            return (density, modulus_of_elasticity, modulus_of_rigidity, yeild_strength, ultimate_tensile_strength, percent_elongation)
        except Exception as e:
            print(e)
        
    def prompt_material_category(self):
        material_categories = [material_category for material_category in self.database.get_material_categories()]
        material_category = material_categories[get_selection([material_category['name'] for material_category in material_categories], indented=True) - 1]
        return material_category['name']
    
    def add_material(self):
        material = self.prompt_material_name()
        category = self.prompt_material_category()
        properties = self.prompt_properties()
        self.database.add_entry(material, category, properties)
    
    def display_materials(self, materials: list):
        if materials:
            num_columns = len(materials[0].keys())
            self.print_headers(materials[0].keys())
            self.print_spacer(num_columns)
            for material in materials:
                print(''.join([str(column).center(self.COLUMN_SPACING) for column in material]))
            self.print_spacer(num_columns)
        else:
            print('No Materials...')

    def display_sorted_materials(self):
        order_by_response = input('Order By (Enter column name): ')
        kwargs = {}
        if order_by_response:
            kwargs['order_by'] = order_by_response
        descending_response = input('Ascending (Y/n): ')
        if descending_response:
            kwargs['descending'] = descending_response[0].upper() == 'N'

        materials = self.database.get_all_entries(**kwargs)
        self.display_materials(materials)
    
    def display_all_materials(self):
        materials = self.database.get_all_entries()
        self.display_materials(materials)        
    
    def delete_material(self, material_name):
        deleted = self.database.delete_material(material_name)
        if deleted:
            print(f"{material_name} succesfully deleted...")
        else:
            print(f"{material_name} was not found...")

    def update_material(self, material_name):
        column = input('Column: ')
        new_value = input('Value: ')
        updated = self.database.update_material(material_name, column, new_value)
        if updated:
            print(f"{material_name}'s {column} succesfully updated...")
        else:
            print(f'{material_name} was not found...')
    
    def print_headers(self, columns):
        print(''.join([f'{self.COLUMN_DISPLAYS.get(column, column).center(self.COLUMN_SPACING)}' for column in columns]))
        
    def print_spacer(self, num_columns):
        print('-'*self.COLUMN_SPACING*num_columns)
    
    def select_entry(self, material):
        return self.database.get_entry_by_material(material)

    def prompt_material_name(self):
        name = input('Material Name: ')
        return name

def get_selection(options, indented=False):
        valid = False
        while not valid:
            try:
                tab = '' if not indented else '\t'
                string = ''
                for i, choice in enumerate(options):
                    string += tab + f'{i+1}) {choice}\n'
                choice = int(input(string + '\nSelection: '))
            except ValueError:
                valid = False
            else:
                valid = (1 <= choice <= len(options))
            if not valid:
                print('Invalid selection, please select again')                
        return choice

if __name__ == '__main__':
    selection = 0
    done_main = False
    while not done_main:
        selection_main = get_selection(['Create Database', 'Edit Database', 'Exit'])
        if selection_main == 1:
            filename = input('Database to Create: ')
            MaterialsDatabase.create_database(filename)
        elif selection_main == 2:
            try:
                filename = input('Database to Edit: ')
                editor = MaterialsDatabaseEditor(filename)
            except sqlite3.OperationalError:
                print(f'{filename} does not currently exist...')
            else:
                done_edit_database = False
                while not done_edit_database:
                    selection_edit = get_selection(['Display All Materials', 'Display Sorted Materials', 'Add Material', 'Select Material', 'Done'])
                    if selection_edit == 1:
                        editor.display_all_materials()
                    elif selection_edit == 2:
                        editor.display_sorted_materials()
                    elif selection_edit == 3:
                        editor.add_material()
                    elif selection_edit == 4:
                        material_name = editor.prompt_material_name()
                        material = editor.select_entry(material_name)
                        if material:
                            done_edit_material = False
                            while not done_edit_material:
                                editor.display_materials(material)
                                selection_edit_material = get_selection(['Update Material', 'Delete Material', 'Done'])
                                if selection_edit_material == 1:
                                    editor.update_material(material_name)
                                    material = editor.select_entry(material_name)
                                elif selection_edit_material == 2:
                                    editor.delete_material(material_name)
                                    done_edit_material = True
                                elif selection_edit_material == 3:
                                    done_edit_material = True
                        else:
                            f"'{material_name}' does not currently exist..."
                    elif selection_edit == 5:
                        done_edit_database = True
        elif selection_main == 3:
            done_main = True