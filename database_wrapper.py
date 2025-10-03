import mysql.connector

class Database:
    def __init__(self, host, gebruiker, wachtwoord, database):
        """
        Initialiseer een nieuwe database

        Parameters:
            host (str): Het adres van de MySQL server.
            gebruiker (str): De gebruikersnaam om in te loggen op de database.
            wachtwoord (str): Het wachtwoord om in te loggen op de database.
            database (str): De naam van de database waarmee verbinding moet worden gemaakt.
        """

        self.host = host
        self.gebruiker = gebruiker
        self.wachtwoord = wachtwoord
        self.database = database
        self.connection = None

    def connect(self):
        """
        Maakt verbinding met de MySQL database met behulp van de verstrekte inloggegevens.
        Print een bericht of de verbinding geslaagd is of niet.
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.gebruiker,
                password=self.wachtwoord,
                database=self.database
            )
            if self.connection:
                print("Verbonden met de database!")
        except mysql.connector.Error as err:
            print(f"Fout bij verbinden met de database: {err}")

    def execute_query(self, query, params = None):
        """
        Voert een SQL-query uit op de verbonden database.

        Parameters:
            query (str): De SQL-query die uitgevoerd moet worden.
            params (tuple, optional): De parameters die worden gekoppeld aan de variabelen in de query. 

        Returns:
            list: Een lijst met de resultaten van de query als het een SELECT query is.
            bool: True als de query succesvol was (bijv. een INSERT/UPDATE/DELETE query), anders False.
            None: Als er geen resultaten zijn om terug te geven (bijv. een INSERT/UPDATE/DELETE query).

        Opmerkingen:
            Als er een fout optreedt bij het uitvoeren van de query, wordt een foutmelding afgedrukt en wordt False geretourneerd.
            Sluit de cursor na de uitvoering van de query.
        """
        if self.connection:
            try:
                cursor = self.connection.cursor(dictionary=True)
                cursor.execute(query, params)
                if cursor.description:
                    return cursor.fetchall()
                else:
                    #print("Aantal rijen geupdated {}".format(cursor.rowcount)) 
                    self.connection.commit()
                    return cursor.rowcount > 0
            except mysql.connector.Error as err:
                print(f"Fout bij uitvoeren van query: {err}")
                return False
            finally:
                cursor.close()
        else:
            print("Niet verbonden met de database. Maak eerst verbinding m.b.v. de connect()-functie")

    def close(self):
        """
        Sluit de verbinding met de MySQL database als deze actief is.
        Print een bericht of de verbinding succesvol is gesloten of als er geen actieve verbinding was om te sluiten.
        """
        if self.connection:
            self.connection.close()
            #print("Databaseverbinding gesloten.")
        else:
            print("Er is geen actieve databaseverbinding om te sluiten.")

