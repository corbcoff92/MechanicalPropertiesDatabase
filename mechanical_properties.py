import argparse
import sqlite3
import sys


class Filter:
    ''' Class representation of a sqlite database filter. '''
    OPERATORS = ['<', '=', '>', '>=', '<=']

    class InvalidOperator(Exception):
        ''' Exception used to indicate that the given operator is invalid. '''
        def __init__(self, operator : str) -> None:
            ''' 
            Creates an intance of an Invalid Operator Exception, including 
            a message indicating the given invalid operator.
            
            Arguments:
                operator : str
                    Invalid operator
            '''
            super().__init__()
            self.message = f'Invalid Operator ({operator}): Must be [{", ".join(Filter.OPERATORS)}]'
        
        def __str__(self):
            ''' Returns string representation of the exception. '''
            return self.message

    def __init__(self, column : str, value: str or float, operator: str) -> None:
        '''
        Creates an instance of a sqlite database filter.
        The string representation of this filter can be directly utilized in sqlite queries.

        Arguments:
            column : str
                Name of the column that is to be filtered.
            value : str or float
                Value to which the given column should be compared.
            operator : str
                Operator indicating how the value should be compared.
        '''
        if operator not in Filter.OPERATORS:
            raise Filter.InvalidOperator(operator)

        self.column = column
        self.value = value
        self.operator = operator
    
    def __str__(self):
        ''' 
        Returns a string representation of this filter for printing. 
        It can also be utilized directly in a sqlite query.
        '''
        return (f'{self.column} {self.operator} "{self.value}"')


class MaterialsDatabase:
    ''' 
    Class represention of a sqlite database containing materials and thier mechanical properties. 
    The actual sqlite database contains multiple tables, however, this class abstracts these tables
    the allow the database to appear as one cohesive whole. This allows the user interaction to 
    remain simple while also utilizing the benefits of relational databases. 
    '''
    DEFUALT_MATERIAL_CATEGORIES = ['Metal', 'Polymer', 'Ceramic', 'Composite', 'Other']

    @staticmethod
    def create_database(filename : str) -> None:
        '''
        Static method that creates an empty database. The database is stored in a file with the given filename.
        
        Arguments:
            filename : str
                Filename that is to be used for the newly created empty database.
        '''
        conn = sqlite3.connect(filename)
        cur = conn.cursor()

        # Create materials table
        cur.execute('''
            CREATE TABLE materials(
                material TEXT UNIQUE NOT NULL PRIMARY KEY,
                category TEXT,
                FOREIGN KEY(category) REFERENCES material_categories(category) ON UPDATE CASCADE);''')
        
        # Create material categories table
        cur.execute('''
            CREATE TABLE material_categories(
                material_category_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
                category TEXT NOT NULL UNIQUE
				);''')

        # Create mechanical properties table
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
        
        # Populate material categories table
        for category in MaterialsDatabase.DEFUALT_MATERIAL_CATEGORIES:
            cur.execute('''
                INSERT INTO material_categories(category) VALUES (?); ''', (category,))

        # Create properties view
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
        
        # Create category summaries view
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

    def __init__(self, filename : str) -> None:
        '''
        Creates an empty sqlite database that can store materials and thier mechanical properties.
        This class contains methods that can be used to interact with the database.
        
        Arguments:
            filename : str
                Name of the file in which the empty database should stored.
        '''
        self.__CONN = sqlite3.connect(f'file:{filename}?mode=rw', uri=True)
        self.__CUR = self.__CONN.cursor()
        self.__CUR.row_factory = sqlite3.Row
        self.__CUR.execute("PRAGMA foreign_keys=ON")
        self.__filters = []
    
    ####################################################################################################
    #                                             Entries                                              #    
    ####################################################################################################
    def __add_material(self, name : str, category : str):
        """ 
        Adds a material to the materials table of this database using the given name and material category.
        The material category must be contained in the material_categories table of this database.

        Arguments:
            name : str
                Name of the materials that is to be added to the database.
            category : str
                Name of the category to which the added material belongs. 
                (This category must be contained in the material_categories table of this database.)
        """
        self.__CUR.execute("INSERT INTO materials(material, category) VALUES (?, ?)", (name, category))

    def __add_mechanical_properties(self, material : str, properties : list) -> None:
        """
        Adds a material's properties to the mechanical properties table of this database using the given material name and its properties.
        The material must be contained in the materials table of this database.

        Arguments:
            material : str
                Name of the material for which the properties are to be added to the database.
            properties : list
                List of values for the properties of the material with the given name.
                (This material must be contained in the materials table of this database.)
        """
        self.__CUR.execute("INSERT INTO mechanical_properties(material, density, modulus_of_elasticity, modulus_of_rigidity, yield_strength, ultimate_tensile_strength, percent_elongation) VALUES (?,?,?,?,?,?,?)", (material, *properties))
    
    def add_entry(self, name : str, category : str, properties : str) -> None:
        """
        Adds an entry to this database with the given material name, material cataegory and material properties.

        Arguments:
            name : str
                Name of the material to be added to this database.
            category : str
                Category of the material to be added to this database.
            properties : list
                Properties of the material to be added to this database.
        """
        try:
            # Add material to materials table
            self.__add_material(name, category)
        except sqlite3.IntegrityError:
            print('A material with that name already exists, please update that material instead...')
        else:
            # Add properties to mechanical properties table
            self.__add_mechanical_properties(name, properties)
            self.__CONN.commit()
    
    def __update_material(self, name : str, column : str, value : str) -> None:
        """
        Updates the specified attribute for the given material.

        Arguments:
            name : str
                Name of the material for which the attribute should be updated.
            column : str
                Name of the attribute which should be updated.
            value : str
                Value to which the attribute should be updated 
        """
        self.__CUR.execute(f'''
            UPDATE materials
            SET
                {column} = ?
            WHERE
                material = ?;
        ''', (value, name))
        self.__CONN.commit()
    
    def __update_mechanical_properties(self, name : str, column : str, value) -> None:
        """
        Updates the specified property for the given material.

        Arguments:
            name : str
                Name of the material for which the property should be updated.
            column : str
                Name of the property which should be updated.
            value : str
                Value to which the property should be updated 
        """
        self.__CUR.execute(f'''
            UPDATE mechanical_properties
            SET
                {column} = ?
            WHERE
                material = ? ;''', (value, name))
        self.__CONN.commit()
    
    def update_entry(self, name, column, value):
        """
        Updates an entry in this database using the given material name, column and value.

        Arguments:
            name : str
                Name of the material that should be updated.
            column : str
                Name of the column which should be updated.
            value : str
                Value to which the column should be updated. 
        """
        if column in ['material', 'category']:
            self.__update_material(name, column, value)
        else:
            if value:
                value = float(value)
            self.__update_mechanical_properties(name, column, value)
        self.__CONN.commit()

        # Update name so that it reflects the newly altered material name
        if column == 'material':
            name = value

        material = self.get_entry_by_material(name)
        return material
    
    def delete_material(self, name : str) -> bool:
        """
        Deletes the entry with the given name from this database.

        Arguments:
            name : str
                Name of the material that should be deleted.
        Returns:
            Boolean indication of whether or not the material has been deleted.
            True if material has been deleted, False otherwise. 
        """
        self.__CUR.execute('''
            DELETE FROM materials
            WHERE material = ?;''', (name,))
        
        # Indicate whether or not the material has been deleted
        if self.__CUR.rowcount == 1:
            self.__CONN.commit()
            return True
        else:
            return False
    
    ####################################################################################################
    #                                             Filters                                              #    
    ####################################################################################################
    def add_filter(self, column : str, value, operator : str) -> None:
        """
        Adds a filter to this database.

        Arguments:
            column : str
                Name of the column that is to be filtered.
            value : str or float
                Value to which the given column should be compared.
            operator : str
                Operator indicating how the value should be compared.
        """
        self.__filters.append(Filter(column, value, operator))

    def remove_filter(self, filter : Filter) -> None:
        """ 
        Removes an existing filter from this database. 

        Arguments:
            filter : Filter
                Existing filter to be removed
        """
        self.__filters.remove(filter)
        
    def clear_filters(self):
        """ Removes all existing filters from this database. """
        self.__filters = []
    
    ####################################################################################################
    #                                            Selections                                            #    
    ####################################################################################################
    def get_all_entries(self, order_by:str='material', descending:bool=False) -> list(sqlite3.Row):
        """
        Returns all entries currently contined in this database.

        Optional Arguments:
            order_by : str, Default = 'material'
                Column that should be used to order the entries.
            descending : bool, Default = False
                Indication of whether or not the column should be ordered in descending order.
                True if descending order, False if ascending order
        Returns:
            List containing all of the entries currently contained in this database.
        """
        results = self.__CUR.execute(f'''
        SELECT
            *
        FROM
	        properties
         ORDER BY
            {order_by + f'{" ASC " if not descending else " DESC "}'} ;''')
        return results.fetchall()

    def get_entry_by_material(self, material : str) -> sqlite3.Row:
        """
        Returns a specific material currently contained in this database.

        Arguments:
            material : str
                Name of material that should be returned.
        Returns:
            Specific material currently contained in this database.
        """
        results = self.__CUR.execute(f'''
        SELECT
            *
        FROM
	        properties
        WHERE
            material = ?;''', (material,))
        return results.fetchone()
    
    def get_filtered_entries(self) -> list(sqlite3.Row):
        """
        Returns all of the entries currently contained in this database that satisfy the requirements of
        this database's current filters.

        Returns:
            List of all the entries currently contained in this database that satisfy the requirements of
            this database's current filters.
        """
        results = self.__CUR.execute(f'''
            SELECT
                *
            FROM
                properties
            WHERE
                {' AND '.join([f'{filter}' for filter in self.__filters])};''')
        return results.fetchall()
    
    def get_category_summaries(self) -> list(sqlite3.Row):
        """
        Returns a list of entries that summarize the characteristics of each material category.

        Returns:
            Returns a list of entries that summarize the characteristics of each material category.
        """
        results = self.__CUR.execute('SELECT * FROM category_summaries')
        return results.fetchall()
    
    ####################################################################################################
    #                                            Attributes                                            #    
    ####################################################################################################
    def get_columns(self) -> list(sqlite3.Row):
        """
        Returns a list of this database's columns.

        Returns:
            List of this database's columns.
        """
        results = self.__CUR.execute('''
            SELECT 
                name 
            FROM 
                PRAGMA_TABLE_INFO('properties');
        ''')
        return results.fetchall()

    def get_material_categories(self) -> list(sqlite3.Row):
        """
        Returns list of material categories currently contained in the database.

        Returns:
            List of material categories currently contained in the database.
        """
        results = self.__CUR.execute('''
        SELECT
            category
        FROM
	        material_categories
         ORDER BY
            material_category_id ASC;''')
        return results.fetchall()
    
    def get_filters(self):
        """
        Returns list of this database's current filters.

        Returns:
            List of this database's current filters.
        """
        return self.__filters


class MaterialsDatabaseEditor:
    """ Class that facilitates user interaction of a material properties database. """
    COLUMN_DISPLAYS = {'material':'Material', 'materials': 'Materials', 'category':'Category', 'density':'ρ(kg/m³)', 'modulus_of_elasticity':'E(GPa)', 'modulus_of_rigidity':'G(GPa)', 'yield_strength':'σy(MPa)', 'ultimate_tensile_strength':'σult(MPa)', 'percent_elongation':r'%EL'}
    COLUMN_SPACING = 11

    def __init__(self, filename : str) -> None:
        """
        Creates an instance of a material properties database editor.
        This instance will be used to edit the database contained in the given filename.

        Arguments:
            filename : str
        """
        self.filename = filename
        self.database = MaterialsDatabase(self.filename)

    ####################################################################################################
    #                                              Prompts                                             #    
    ####################################################################################################
    def __prompt_material_name(self) -> str:
        """
        Prompts the user for the name of a material using the command line, 
        ensuring that the name is not blank.

        Returns:
            Name of the material retrieved from the user.
        Raises:
            ValueError
                If name is blank.
        """
        name = input('\tMaterial Name: ')

        if not name.strip():
            raise ValueError()

        return name
    
    def __prompt_material_category(self) -> str:
        """
        Prompts the user for a material category name using the command line.

        Returns:
            Material category name retrieved from the user.
        """
        material_categories = [material_category for material_category in self.database.get_material_categories()]
        material_category = material_categories[get_selection([material_category['category'] for material_category in material_categories], indented=True) - 1]
        return material_category['category']
            
    def __prompt_properties(self) -> list(float):
        """
        Prompts the user for a value for each of the properties contained in the material properties database using the command line.

        Returns:
            List of values for each of the properties contained in the material properties database.
        """
        # Prompt properties
        density = input('\tDensity (kg/m³): ')
        modulus_of_elasticity = input('\tModulus of Elasticity (GPa): ')
        modulus_of_rigidity = input('\tModulus of Rigidity (GPa): ')
        yeild_strength = input('\tYield Strength (MPa): ')
        ultimate_tensile_strength = input('\tUltimate Tensile Strength (MPa): ')
        percent_elongation = input('\tPercent Elongation (%): ')

        properties = [density, modulus_of_elasticity, modulus_of_rigidity, yeild_strength, ultimate_tensile_strength, percent_elongation]
        
        # Convert properties
        for i in range(len(properties)):
            if properties[i]:
                properties[i] = float(properties[i])

        return properties
    
    def __prompt_property_column(self) -> str:
        """
        Prompts the user for the name of a property contained in 
        the material properties database using the command line.

        Returns:
            Name of a property contained in the material properties database.
        """
        columns = self.database.get_columns()
        selection = get_selection([self.COLUMN_DISPLAYS.get(column['name'], column['name']) for column in columns], indented=True)
        return columns[selection - 1]['name']
    
    ####################################################################################################
    #                                            Materials                                             #
    ####################################################################################################
    def add_material(self) -> None:
        """ Prompts the user for & adds a material to this editor's database. """
        try:
            material = self.__prompt_material_name()
            category = self.__prompt_material_category()
            properties = self.__prompt_properties()
            self.database.add_entry(material, category, properties)
        except ValueError:
            print('Invalid value')
    
    def select_entry(self) -> sqlite3.Row:
        """ 
        Prompts the user for & selects a material from this editor's database. 
        
        Returns:
            Material from this editor's database.
        """
        material_name = self.__prompt_material_name()
        material = self.database.get_entry_by_material(material_name)

        if not material:
            print(f"'{material_name}' does not currently exist...")

        return material
    
    def update_material(self, material):
        """
        Prompts for & updates a property from the given material.

        Arguments:
            material : sqlite3.Row
                Material that is to be updated.
        Returns:
            Updated material if updated succesfully, otherwise given material. 
        """
        material_name = material['material']
        column = self.__prompt_property_column()

        if column != 'category':
            new_value = input(f'\t{self.COLUMN_DISPLAYS.get(column, column)}: ')
        else:
            new_value = self.__prompt_material_category()

        try:
            updated_material = self.database.update_entry(material_name, column, new_value)
            if updated_material:
                material = updated_material
                print(f"{material_name}'s {self.COLUMN_DISPLAYS.get(column, column)} succesfully updated...")
        except sqlite3.IntegrityError as e:
            print('A material with that name already exists...')

        return material

    def delete_material(self, material : sqlite3.Row) -> None:
        """
        Deletes the given material from this editor's database.

        Arguments:
            material : sqlite3.Row
                Material that is to be deleted. 
        """
        material_name = material['material']
        deleted = self.database.delete_material(material_name)

        # Indicate whether or not the material has been deleted
        if deleted:
            print(f"{material_name} succesfully deleted...")
        else:
            print(f"{material_name} was not found...")
    
    ####################################################################################################
    #                                             Filters                                              #
    ####################################################################################################
    def add_filter(self) -> None:
        """ Prompts for & adds a filter to this editor's database. """
        try:
            column = self.__prompt_property_column()

            print(self.COLUMN_DISPLAYS.get(column, column))
            operator = input(f'Operator {Filter.OPERATORS}: ') if column not in ['material', 'category'] else '='

            if column == 'material':
                value = input('Name: ')
            elif column == 'category':
                value = self.__prompt_material_category()
            else:
                value = input(f'Value: ')

            self.database.add_filter(column, value, operator)
        except Filter.InvalidOperator as e:
            print(e)
    
    def remove_filter(self) -> None:
        """ Prompts for & removes a filter from this editor's database. """
        filters = self.database.get_filters()

        if filters:
            selection = get_selection([self.__get_filter_string(filter) for filter in filters], indented=True)
            filter = filters[selection - 1]
            self.database.remove_filter(filter)
        else:
            print('No filters to remove...')
    
    def clear_filters(self) -> None:
        """ Removes all filters from this editor's database. """
        self.database.clear_filters()

    ####################################################################################################
    #                                             Display                                              #
    ####################################################################################################
    def __print_headers(self, columns:list[str]) -> None:
        """ 
        Prints a header containing the given columns.

        Arguments:
            columns : list[str]
                List containing column headers to be displayed.
        """
        print(''.join([f'{self.COLUMN_DISPLAYS.get(column, column).center(self.COLUMN_SPACING)}' for column in columns]))
        
    def __print_spacer(self, num_columns : int) -> None:
        """
        Prints a spacer large enough to separate the given number of columns.
        
        Arguments:
            num_columns : int
                Number of columns that the spacer will be used to separate.
        """
        print('-'*self.COLUMN_SPACING*num_columns)
    
    def __get_filter_string(self, filter : Filter) -> str:
        """ 
        Returns human readable string representing the given filter. 
        
        Arguments:
            filter : Filter
                Filter that is to be displayed
        Returns:
            Human readable string representing the given filter.
        """
        return f'{self.COLUMN_DISPLAYS.get(filter.column, filter.column)} {filter.operator} {filter.value}'
    
    def display_filters(self) -> None:
        """ Displays the current filters for this editor's database. """
        filters = self.database.get_filters()
        
        print('Filters')
        if filters:
            for filter in self.database.get_filters():
                print(f'\t{self.__get_filter_string(filter)}')
        else:
            print('\tNo filters...')
    
    def display_materials(self, materials: list[sqlite3.Row]) -> None:
        """
        Displays the given list of materials using the command line.

        Arguments:
            materials : list[sqlite3.Row]
                Materials that are to be displayed.
        """
        if materials:
            num_columns = len(materials[0].keys())

            self.__print_headers(materials[0].keys())
            self.__print_spacer(num_columns)
            for material in materials:
                print(''.join([str(column).center(self.COLUMN_SPACING) for column in material]))
            self.__print_spacer(num_columns)
        else:
            print('No Materials...')
    
    def display_all_materials(self):
        """ Displays all of the materials currently contained in this editor's database. """
        materials = self.database.get_all_entries()
        self.display_materials(materials)
    
    def display_material(self):
        """ Prompts for & displays a specific material currently contained in this editor's database. """
        material_name = self.__prompt_material_name()        
        material = self.database.get_entry_by_material(material_name)
        self.display_materials([material])

    def display_sorted_materials(self):
        """ Prompts for & displays all materials currently contained in this editor's database ordered by the prompted column. """
        kwargs = {}  # Keyword arguments
        
        print('Order By')
        order_by_response = self.__prompt_property_column()
        if order_by_response:
            kwargs['order_by'] = order_by_response
        
        descending_response = input('Ascending (Y/n): ')
        if descending_response:
            kwargs['descending'] = descending_response[0].upper() == 'N'

        materials = self.database.get_all_entries(**kwargs)
        self.display_materials(materials)
    
    def display_filtered_materials(self):
        """ Displays all materials currently contained in this editor's database that satisfy the database's current filters. """
        if self.database.get_filters():
            materials = self.database.get_filtered_entries()
            self.display_materials(materials)
        else:
            # Display all materials if no filters are present
            self.display_all_materials()
    
    def display_category_summaries(self):
        """ Displays category summaries that summarize the properties of each material category currently contained in this editor's database. """
        material_summaries = self.database.get_category_summaries()
        print(' ' * self.COLUMN_SPACING * 2 + f"{'Averages'.center(self.COLUMN_SPACING * (len(material_summaries[0]) - 2) - 2)}")
        self.display_materials(material_summaries)
    
    ####################################################################################################
    #                                              Editor                                              #
    ####################################################################################################
    def edit_database(self):
        """ Command line interface that facilitates user interaction. """
        done_database = False
        while not done_database:
            print(f'Database: {self.filename}')
            selection_database = get_selection(['View Database', 'Edit Database', 'Done'])
            if selection_database == 1:
                done_view_database = False
                while not done_view_database:
                    print(f'Display Database: {self.filename}')
                    selection_view = get_selection(['Display All Materials', 'Display Material', 'Display Sorted Materials', 'Display Filtered Materials', 'Display Category Summaries', 'Done'])
                    if selection_view == 1:
                        self.display_all_materials()
                    elif selection_view == 2:
                        self.display_material()
                    elif selection_view == 3:
                        self.display_sorted_materials()
                    elif selection_view == 4:
                        done_filter = False
                        while not done_filter:
                            self.display_filters()
                            selection_filter = get_selection(['Add filter', 'Remove Filter', 'Apply Filters', 'Clear Filters', 'Done'])
                            if selection_filter == 1:
                                self.add_filter()
                            elif selection_filter == 2:
                                self.remove_filter()
                            elif selection_filter == 3:
                                self.display_filtered_materials()
                            elif selection_filter == 4:
                                self.clear_filters()
                            elif selection_filter == 5:
                                done_filter = True
                    elif selection_view == 5:
                        self.display_category_summaries()
                    elif selection_view == 6:
                        done_view_database = True
            elif selection_database == 2:
                done_edit_database = False
                while not done_edit_database:
                    print(f'Edit Database: {self.filename}')
                    selection_edit = get_selection(['Display Materials', 'Add Material', 'Edit Material', 'Done'])
                    if selection_edit == 1:
                        self.display_all_materials()
                    elif selection_edit == 2:
                        self.add_material()
                    elif selection_edit == 3:
                        material = self.select_entry()
                        if material:
                            done_edit_material = False
                            while not done_edit_material:
                                print(f'Selected Material')
                                self.display_materials([material])
                                selection_edit_material = get_selection(['Update Material', 'Delete Material', 'Done'])
                                if selection_edit_material == 1:
                                    material = self.update_material(material)
                                elif selection_edit_material == 2:
                                    self.delete_material(material)
                                    done_edit_material = True
                                elif selection_edit_material == 3:
                                    done_edit_material = True
                    elif selection_edit == 4:
                        done_edit_database = True
            elif selection_database == 3:
                done_database = True


def get_selection(options : list[str], indented : bool=False) -> int:
    """ 
    Displays the given options & gets a selection from the user using the command line.
    This includes selection validation, reprompting the user until a valid option is 
    selected.

    Arguments:
        options : list[str]
            List of options that will be displayed and selected
    Optional Arguments:
        indented : bool, Default = False
            Indication of whether or not the list of options should be indented when displayed.
            True if should be indented, false otherwise.
    """
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


def command_line():
    """ Command line interface that integrates the Material Properties Database & Material Proerties Database Editor. """
    done_main = False
    while not done_main:
        print('Mechanical Properties Database Editor')
        selection_main = get_selection(['Create New Database', 'Open Existing Database', 'Exit'])
        if selection_main == 1:
            filename = input('Database to Create: ')
            MaterialsDatabase.create_database(filename)
        elif selection_main == 2:
            filename = input('Database to Edit: ')
            try:
                editor = MaterialsDatabaseEditor(filename)
            except sqlite3.OperationalError:
                print(f'{filename} does not currently exist...')
            else:
                editor.edit_database()
        elif selection_main == 3:
            done_main = True


if __name__ == '__main__':
    # Command line arguments
    num_args = len(sys.argv)

    # No command line arguments
    if num_args == 1:
        command_line()
    else:
        # Parse command line arguments
        parser = argparse.ArgumentParser()
        parser.add_argument('function', help='Databases function that you would like to perform [create or edit].')
        parser.add_argument('filename', help='Name of the database file')
        args = parser.parse_args()

        if args.function == 'create':
            MaterialsDatabase.create_database(args.filename)
        elif args.function == 'edit':
            try:
                editor = MaterialsDatabaseEditor(args.filename)
            except sqlite3.OperationalError:
                print(f'{args.filename} does not currently exist...')
            else:
                editor.edit_database()
        else:
            parser.error('Invalid function, must be create or edit...')