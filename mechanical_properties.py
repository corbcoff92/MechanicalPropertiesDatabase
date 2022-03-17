import sqlite3

class Filter:
    OPERATORS = ['<', '=', '>', '>=', '<=']

    class InvalidOperator(Exception):
        def __init__(self, operator):
            super().__init__()
            self.message = f'Invalid Operator ({operator}): Must be [{", ".join(Filter.OPERATORS)}]'
        
        def __str__(self):
            return self.message

    def __init__(self, column, value, operator):
        if operator not in Filter.OPERATORS:
            raise Filter.InvalidOperator(operator)

        self.column = column
        self.value = value
        self.operator = operator
    
    def __str__(self):
        return (f'{self.column} {self.operator} "{self.value}"')

class MaterialsDatabase:
    DEFUALT_MATERIAL_CATEGORIES = ['Metal', 'Polymer', 'Ceramic', 'Composite', 'Other']

    def __init__(self, filename):
        self.__CONN = sqlite3.connect(f'file:{filename}?mode=rw', uri=True)
        self.__CUR = self.__CONN.cursor()
        self.__CUR.row_factory = sqlite3.Row
        self.__CUR.execute("PRAGMA foreign_keys=ON")
        self.__filters = []
    
    def get_filters(self):
        return self.__filters

    def remove_filter(self, filter):
        self.__filters.remove(filter)
        
    def clear_filters(self):
        self.__filters = []

    def add_filter(self, column, value, operator):
        self.__filters.append(Filter(column, value, operator))
        
    def __add_material(self, name, category):
            self.__CUR.execute("INSERT INTO materials(material, category) VALUES (?, ?)", (name, category))

    def __add_mechanical_properties(self, material, properties):
        self.__CUR.execute("INSERT INTO mechanical_properties(material, density, modulus_of_elasticity, modulus_of_rigidity, yield_strength, ultimate_tensile_strength, percent_elongation) VALUES (?,?,?,?,?,?,?)", (material, *properties))
    
    def add_entry(self, name, category, properties):
        try:
            self.__add_material(name, category)
        except sqlite3.IntegrityError:
            print('A material with that name already exists, please update that material instead...')
        else:
            self.__add_mechanical_properties(name, properties)
            self.__CONN.commit()
    
    def get_filtered_entries(self):
        results = self.__CUR.execute(f'''
            SELECT
                *
            FROM
                properties
            WHERE
                {' AND '.join([f'{filter}' for filter in self.__filters])};''')
        return results.fetchall()

    def update_entry(self, name, column, value):
        if column in ['material', 'category']:
            self.update_material(name, column, value)
        else:
            if value:
                value = float(value)
            self.update_mechanical_properties(name, column, value)
        self.__CONN.commit()
        return self.__CUR.rowcount == 1
    
    def update_material(self, name, column, value):
        self.__CUR.execute(f'''
            UPDATE materials
            SET
                {column} = ?
            WHERE
                material = ?;
        ''', (value, name))
        self.__CONN.commit()
    
    def update_mechanical_properties(self, name, column, value):
        self.__CUR.execute(f'''
            UPDATE mechanical_properties
            SET
                {column} = ?
            WHERE
                material = ? ;''', (value, name))
        self.__CONN.commit()

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
            WHERE material = ?;''', (name,))
        
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
                material TEXT UNIQUE NOT NULL PRIMARY KEY,
                category TEXT,
                FOREIGN KEY(category) REFERENCES material_categories(category) ON UPDATE CASCADE);''')

        cur.execute('''
            CREATE TABLE material_categories(
                material_category_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
                category TEXT NOT NULL UNIQUE
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
                FOREIGN KEY(material) REFERENCES materials(material) ON UPDATE CASCADE ON DELETE CASCADE);''')
                

        for category in MaterialsDatabase.DEFUALT_MATERIAL_CATEGORIES:
            cur.execute('''
                INSERT INTO material_categories(category) VALUES (?); ''', (category,))

        cur.execute('''
            CREATE VIEW properties
            AS
            SELECT
                materials.material,
                category,
                density,
                modulus_of_elasticity,
                modulus_of_rigidity,
                yield_strength,
                ultimate_tensile_strength,
                percent_elongation
            FROM
                materials
            INNER JOIN material_categories USING(category)
            INNER JOIN mechanical_properties USING(material);''')
        
        cur.execute('''
            CREATE VIEW category_summaries 
            AS
            SELECT
                category,
                count(material) AS materials,
                IFNULL(avg(density), "") AS density,
                IFNULL(avg(modulus_of_elasticity), "") AS modulus_of_elasticity,
                IFNULL(avg(modulus_of_rigidity), "") AS modulus_of_rigidity,
                IFNULL(avg(yield_strength), "") AS yield_strength,
                IFNULL(avg(ultimate_tensile_strength), "") AS ultimate_tensile_strength,
                IFNULL(avg(percent_elongation), "") AS percent_elongation
            FROM
                material_categories
            LEFT JOIN properties USING(category)
            GROUP BY
                category
            ORDER BY
                material_category_id ASC; 
        ''')

        conn.commit()

    def get_columns(self):
        results = self.__CUR.execute('''
            SELECT 
                name 
            FROM 
                PRAGMA_TABLE_INFO('properties');
        ''')
        return results.fetchall()

    def get_material_categories(self):
        results = self.__CUR.execute('''
        SELECT
            category
        FROM
	        material_categories
         ORDER BY
            material_category_id ASC;''')
        return results.fetchall()
    
    def get_category_summaries(self):
        results = self.__CUR.execute('SELECT * FROM category_summaries')
        return results.fetchall()

class MaterialsDatabaseEditor:
    COLUMN_DISPLAYS = {'material':'Material', 'materials': 'Materials', 'category':'Category', 'density':'ρ(kg/m³)', 'modulus_of_elasticity':'E(GPa)', 'modulus_of_rigidity':'G(GPa)', 'yield_strength':'σy(MPa)', 'ultimate_tensile_strength':'σult(MPa)', 'percent_elongation':r'%EL'}
    COLUMN_SPACING = 11

    def __init__(self, filename):
        self.database = MaterialsDatabase(filename)

    def prompt_name(self):
        name = input('\tMaterial Name: ')
        return name
            
    def prompt_properties(self):
        density = input('\tDensity (kg/m³): ')
        modulus_of_elasticity = input('\tModulus of Elasticity (GPa): ')
        modulus_of_rigidity = input('\tModulus of Rigidity (GPa): ')
        yeild_strength = input('\tYield Strength (MPa): ')
        ultimate_tensile_strength = input('\tUltimate Tensile Strength (MPa): ')
        percent_elongation = input('\tPercent Elongation (%): ')

        properties = [density, modulus_of_elasticity, modulus_of_rigidity, yeild_strength, ultimate_tensile_strength, percent_elongation]
        for i in range(len(properties)):
            if properties[i]:
                properties[i] = float(properties[i])
        return properties
        
    def prompt_material_category(self):
        material_categories = [material_category for material_category in self.database.get_material_categories()]
        material_category = material_categories[get_selection([material_category['category'] for material_category in material_categories], indented=True) - 1]
        return material_category['category']
    
    def prompt_property_column(self):
        columns = self.database.get_columns()
        selection = get_selection([self.COLUMN_DISPLAYS.get(column['name'], column['name']) for column in columns], indented=True)
        return columns[selection - 1]['name']

    def get_filter_string(self, filter):
        return f'{self.COLUMN_DISPLAYS.get(filter.column, filter.column)} {filter.operator} {filter.value}'

    def display_filters(self):
        filters = self.database.get_filters()
        print('Filters')
        if filters:
            for filter in self.database.get_filters():
                print(f'\t{self.get_filter_string(filter)}')
        else:
            print('\tNo filters...')

    def add_material(self):
        try:
            material = self.prompt_material_name()
            category = self.prompt_material_category()
            properties = self.prompt_properties()
            self.database.add_entry(material, category, properties)
        except ValueError:
            print('Invalid value')
    
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
        print('Order By')
        order_by_response = self.prompt_property_column()
        kwargs = {}
        if order_by_response:
            kwargs['order_by'] = order_by_response
        descending_response = input('Ascending (Y/n): ')
        if descending_response:
            kwargs['descending'] = descending_response[0].upper() == 'N'

        materials = self.database.get_all_entries(**kwargs)
        self.display_materials(materials)
    
    def add_filter(self):
        try:
            column = self.prompt_property_column()
            print(self.COLUMN_DISPLAYS.get(column, column))
            operator = input(f'Operator {Filter.OPERATORS}: ') if column not in ['material', 'category'] else '='
            if column == 'material':
                value = input('Name: ')
            elif column == 'category':
                value = self.prompt_material_category()
            else:
                value = input(f'Value: ')
            self.database.add_filter(column, value, operator)
        except Filter.InvalidOperator as e:
            print(e)
    
    def remove_filter(self):
        filters = self.database.get_filters()
        if filters:
            selection = get_selection([self.get_filter_string(filter) for filter in filters], indented=True)
            filter = filters[selection - 1]
            self.database.remove_filter(filter)
        else:
            print('No filters to remove...')
    
    def apply_filters(self):
        if self.database.get_filters():
            materials = self.database.get_filtered_entries()
            self.display_materials(materials)
        else:
            self.display_all_materials()
    
    def clear_filters(self):
        self.database.clear_filters()

    def display_all_materials(self):
        materials = self.database.get_all_entries()
        self.display_materials(materials)

    def display_material(self):
        material_name = self.prompt_material_name()        
        material = self.database.get_entry_by_material(material_name)
        self.display_materials(material)
    
    def delete_material(self, material_name):
        deleted = self.database.delete_material(material_name)
        if deleted:
            print(f"{material_name} succesfully deleted...")
        else:
            print(f"{material_name} was not found...")

    def update_material(self, material_name):
        column = self.prompt_property_column()
        if column != 'category':
            new_value = input(f'\t{self.COLUMN_DISPLAYS.get(column, column)}: ')
        else:
            new_value = self.prompt_material_category()
        try:
            updated = self.database.update_entry(material_name, column, new_value)
            if updated:
                print(f"{material_name}'s {self.COLUMN_DISPLAYS.get(column, column)} succesfully updated...")
            else:
                print(f'{material_name} was not found...')    
            return material_name if column != 'material' else new_value
        except sqlite3.IntegrityError as e:
            print(e)
            print('A material with that name already exists...')
    
    def print_headers(self, columns):
        print(''.join([f'{self.COLUMN_DISPLAYS.get(column, column).center(self.COLUMN_SPACING)}' for column in columns]))
        
    def print_spacer(self, num_columns):
        print('-'*self.COLUMN_SPACING*num_columns)
    
    def select_entry(self, material):
        return self.database.get_entry_by_material(material)

    def prompt_material_name(self):
        name = input('\tMaterial Name: ')
        if not name.strip():
            raise ValueError()
        return name
    
    def display_category_summaries(self):
        material_summaries = self.database.get_category_summaries()
        print(' ' * self.COLUMN_SPACING * 2 + f"{'Averages'.center(self.COLUMN_SPACING * (len(material_summaries[0]) - 2) - 2)}")
        self.display_materials(material_summaries)
    
def get_selection(options, indented=False):
        valid = False
        while not valid:
            try:
                tab = '' if not indented else '\t'
                string = ''
                for i, choice in enumerate(options):
                    string += tab + f'{i+1}) {choice}\n'
                choice = int(input(string + 'Selection: '))
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
        print('Mechanical Properties Database Editor')
        selection_main = get_selection(['Create New Database', 'Open Existing Database', 'Exit'])
        if selection_main == 1:
            filename = input('Database to Create: ')
            MaterialsDatabase.create_database(filename)
        elif selection_main == 2:
            try:
                filename = input('Database to Open: ')
                editor = MaterialsDatabaseEditor(filename)
            except sqlite3.OperationalError:
                print(f'{filename} does not currently exist...')
            else:
                done_database = False
                while not done_database:
                    print(f'Database: {filename}')
                    selection_database = get_selection(['View Database', 'Edit Database', 'Done'])
                    if selection_database == 1:
                        done_view_database = False
                        while not done_view_database:
                            print(f'Display Database: {filename}')
                            selection_view = get_selection(['Display All Materials', 'Display Material', 'Display Sorted Materials', 'Display Filtered Materials', 'Display Category Summaries', 'Done'])
                            if selection_view == 1:
                                editor.display_all_materials()
                            elif selection_view == 2:
                                editor.display_material()
                            elif selection_view == 3:
                                editor.display_sorted_materials()
                            elif selection_view == 4:
                                done_filter = False
                                while not done_filter:
                                    editor.display_filters()
                                    selection_filter = get_selection(['Add filter', 'Remove Filter', 'Apply Filters', 'Clear Filters', 'Done'])
                                    if selection_filter == 1:
                                        editor.add_filter()
                                    elif selection_filter == 2:
                                        editor.remove_filter()
                                    elif selection_filter == 3:
                                        editor.apply_filters()
                                    elif selection_filter == 4:
                                        editor.clear_filters()
                                    elif selection_filter == 5:
                                        done_filter = True
                            elif selection_view == 5:
                                editor.display_category_summaries()
                            elif selection_view == 6:
                                done_view_database = True
                    elif selection_database == 2:
                        done_edit_database = False
                        while not done_edit_database:
                            print(f'Edit Database: {filename}')
                            selection_edit = get_selection(['Display Materials', 'Add Material', 'Edit Material', 'Done'])
                            if selection_edit == 1:
                                editor.display_all_materials()
                            elif selection_edit == 2:
                                editor.add_material()
                            elif selection_edit == 3:
                                material_name = editor.prompt_material_name()
                                material = editor.select_entry(material_name)
                                if material:
                                    done_edit_material = False
                                    while not done_edit_material:
                                        print(f'Selected Material')
                                        editor.display_materials(material)
                                        selection_edit_material = get_selection(['Update Material', 'Delete Material', 'Done'])
                                        if selection_edit_material == 1:
                                            material_name = editor.update_material(material_name)
                                            material = editor.select_entry(material_name)
                                        elif selection_edit_material == 2:
                                            editor.delete_material(material_name)
                                            done_edit_material = True
                                        elif selection_edit_material == 3:
                                            done_edit_material = True
                                else:
                                    print(f"'{material_name}' does not currently exist...")
                            elif selection_edit == 4:
                                done_edit_database = True
                    elif selection_database == 3:
                        done_database = True
        elif selection_main == 3:
            done_main = True