# Overview
There are many types of engineering analysis. Each of these can include analysis 
performed using pen and paper or analysis performed through numerical methods and 
software. Programmatic analysis allows for the quick adjustment of variables to identify 
different results. Almost all these engineering analyses require the mechanical properties of the 
materials being used. These properties are often provided in the form of printed data tables. 
This can be convenient for pen and paper analyses but is often a source of disconnect when it 
comes to custom programmatic analyses, as each individual value must be found and manually 
entered for each program written. This Python program allows the user the ability to store and access this data programmatically, using a SQLite database. The program alone can improve pen 
and paper analyses by allowing specific properties to be quickly identified. It also provides tools that can also be utilized in other custom programmatic analyses, enabling the program to be much more robust.

The program contains a command line interface that allows the user to easily interact with the integrated database. The command line interface can be accessed by executing the main `mechanical_properties.py` file directly from a command line. The program can also function as a command line program utilizing command line arguments. These arguments provide additional entry points to the program, for example `mechanical_properties create [filaname]` for directly creating a blank database & `mechanical_properties edit [filename]` for directly editing an existing database.

A demonstration of the program is provided here: [Mechanical Propereties Program Demonstration Video](https://youtu.be/Cjg4cRrvHQY)

# Relational Database

The integrated relational database stores mechanical properties of materials. This relational database constists of the following tables:
* materials
    - material
    - category
* material_categories
    - material_category_id
    - category
* mechanical_properties
    - material
    - density
    - modulus_of_elasticty
    - modulus_of_rigidity
    - yield_strength
    - ultimate_tensile_strength
    - percent_elongation

The database also contains the following views:
* properties
    - material
    - density
    - modulus_of_elasticty
    - modulus_of_rigidity
    - yield_strength
    - ultimate_tensile_strength
    - percent_elongation
* category_summaries
    - category
    - materials
    - density
    - modulus_of_elasticty
    - modulus_of_rigidity
    - yield_strength
    - ultimate_tensile_strength
    - percent_elongation

The category summaries view utilizes aggregate funcitons to summarize the properties of materials of each of the different material categories 

# Development Environment
* Python 3.10.1
    - `sqlite3` library
* Visual Studio Code | Version 1.64.2

# Useful Websites
* [Python sqlite3 Documentation](https://docs.python.org/3.8/library/sqlite3.html) (official site)
* [How To Use the sqlite3 Module in Python 3](https://www.digitalocean.com/community/tutorials/how-to-use-the-sqlite3-module-in-python-3) (tutorial site)
* [SQLite Tutorial](https://www.sqlitetutorial.net/) (tutorial site)
* [SQLite - Python](https://www.tutorialspoint.com/sqlite/sqlite_python.htm) (tutorial site)
* [Python SQLite Tutorial — The Ultimate Guide](https://towardsdatascience.com/python-sqlite-tutorial-the-ultimate-guide-fdcb8d7a4f30) (tutorial site)

# Future Work
* Additional Properties
* Develop module that can be imported