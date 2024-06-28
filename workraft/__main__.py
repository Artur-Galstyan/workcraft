import asyncio

import fire

from workraft import peon, stronghold
from workraft.db import get_db_config


class Workraft:
    """Workraft: A simple distributed task system."""

    def stronghold(self):
        """
        Start the Stronghold.

        The Stronghold is responsible for managing the task queue
        and coordinating Peons.
        It sets up the database and handles system-wide tasks.
        """

        db_config = get_db_config()
        asyncio.run(stronghold.run_stronghold(db_config))

    def peon(self):
        """
        Start a Peon.

        Peons are worker units that fetch and execute tasks from the Stronghold.
        Each Peon runs independently and communicates with the Stronghold via
        the database.
        """

        db_config = get_db_config()
        asyncio.run(peon.run_peon(db_config))

    def zugzug(self):
        """
        Display information about Workraft.

        This command provides an overview of available commands and their purposes.
        """
        print("Workraft: A simple distributed task system")
        print("Commands:")
        print("  stronghold - Start the Stronghold")
        print("  peon - Start a Peon")
        print("  zugzug - Display this information")


def main():
    fire.Fire(Workraft)


if __name__ == "__main__":
    main()
