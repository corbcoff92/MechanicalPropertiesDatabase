import sqlite3

class MaterialsDatabase:
    DATA_COLUMNS = ['name', 'density', 'modulus_of_elasticity', 'modulus_of_rigidity', 'yield_strength', 'ultimate_tensile_strength', 'percent_elongation']

    def __init__(self, filename):
        self.__CONN = sqlite3.connect(f'file:{filename}?mode=rw', uri=True)
        self.__CUR = self.__CONN.cursor()
        self.__CUR.row_factory = sqlite3.Row

    def add_material(self, material):
        try:
            self.__CUR.execute("INSERT INTO mechanical_properties(name, density, modulus_of_elasticity, modulus_of_rigidity, yield_strength, ultimate_tensile_strength, percent_elongation) VALUES (?,?,?,?,?,?,?)", material)
            self.__CONN.commit()
        except sqlite3.IntegrityError:
            print('A material with that name already exists, please update that material instead...')
    
    def select_material(self, name):
        results = self.__CUR.execute(f'''
            SELECT
                ?
            FROM
                mechanical_properties
            WHERE
                name=?;''', (" ".join(MaterialsDatabase.DATA_COLUMNS), name,))
        return results.fetchone()

    def select_all_materials(self, columns=DATA_COLUMNS, order_by='name', descending=False):
        results = self.__CUR.execute(f'''
        SELECT
            {", ".join(columns)}
        FROM
	        mechanical_properties
         ORDER BY
            {order_by + f'{" ASC " if not descending else " DESC "}'} ;''')
        return results.fetchall()
    
    def delete_material(self, name):
        self.__CUR.execute('''
            DELETE FROM mechanical_properties
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
            CREATE TABLE IF NOT EXISTS mechanical_properties(
                material_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                name TEXT NON NULL UNIQUE,
                density INTEGER NON NULL,
                modulus_of_elasticity INTEGER NON NULL,
                modulus_of_rigidity INTEGER NON NULL,
                yield_strength INTEGER,
                ultimate_tensile_strength INTEGER NON NULL,
                percent_elongation INTEGER,
                type TEXT
            );''')

class MaterialsDatabaseEditor:
    COLUMN_DISPLAYS = {'name':'Material', 'density':'ρ(kg/m³)', 'modulus_of_elasticity':'E(GPa)', 'modulus_of_rigidity':'G(GPa)', 'yield_strength':'σy(MPa)', 'ultimate_tensile_strength':'σult(MPa)', 'percent_elongation':r'%EL'}
    COLUMN_SPACING = 11

    def __init__(self, filename):
        self.database = MaterialsDatabase(filename)

    def prompt_material(self):
        print('Add Material:')
        try:
            name = input('\tMaterial Name: ')
            density = int(input('\tDensity (kg/m³): '))
            modulus_of_elasticity = int(input('\tModulus of Elasticity (GPa): '))
            modulus_of_rigidity = int(input('\tModulus of Rigidity (GPa): '))
            yeild_strength = int(input('\tYield Strength (MPa): '))
            ultimate_tensile_strength = int(input('\tUltimate Tensile Strength (MPa): '))
            percent_elongation = int(input('\tPercent Elongation (%): '))
            
            return (name, density, modulus_of_elasticity, modulus_of_rigidity, yeild_strength, ultimate_tensile_strength, percent_elongation)
        except Exception as e:
            print(e)
    
    def add_material(self):
        material = self.prompt_material()
        self.database.add_material(material)
    
    def display_materials(self, materials: list):
        if materials:
            num_columns = len(materials[0].keys())
            self.print_headers(materials[0].keys())
            self.print_spacer(num_columns)
            for material in materials:
                print(''.join([str(material[column]).center(self.COLUMN_SPACING) for column in material.keys()]))
            self.print_spacer(num_columns)
        else:
            print('No Materials...')

    def display_all_materials(self):
        order_by_response = input('Order By (Enter column name): ')
        kwargs = {}
        if order_by_response:
            kwargs['order_by'] = order_by_response
        descending_response = input('Ascending (Y/n): ')
        if descending_response:
            kwargs['descending'] = descending_response[0].upper() == 'N'

        materials = self.database.select_all_materials(**kwargs)
        self.display_materials(materials)
    
    def delete_material(self):
        material = self.prompt_material_name()
        deleted = self.database.delete_material(material)
        if deleted:
            print(f'{material} succesfully deleted...')
        else:
            print(f'{material} was not found...')

    
    def print_headers(self, columns):
        print(''.join([f'{self.COLUMN_DISPLAYS.get(column, column).center(self.COLUMN_SPACING)}' for column in columns]))
        
    def print_spacer(self, num_columns):
        print('-'*self.COLUMN_SPACING*num_columns)

    def prompt_material_name(self):
        name = input('Material Name: ')
        return name

def get_selection(options):
        valid = False
        while not valid:
            try:
                choice = int(input('\n'.join([f'{i+1}) {choice}' for i, choice in enumerate(options)]) + '\nSelection: '))
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
                done_edit = False
                while not done_edit:
                    selection_edit = get_selection(['Display Materials', 'Add Material', 'Delete Material', 'Done'])
                    if selection_edit == 1:
                        editor.display_all_materials()
                    elif selection_edit == 2:
                        editor.add_material()
                    elif selection_edit == 3:
                        editor.delete_material()
                    elif selection_edit == 4:
                        done_edit = True
        elif selection_main == 3:
            done_main = True