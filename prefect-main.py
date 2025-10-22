from prefect import flow, task
import random


@task
def get_customer_ids() -> list[str]:
    # Fetch customer IDs from a database or API
    return [f"customer{n}" for n in random.choices(range(100), k=10)]


@flow
def my_favorite_function():
    print("What is your favorite number?")
    fav_number = 42
    customer_ids = get_customer_ids()
    print(f"Favorite number: {fav_number}")
    print(f"Customer IDs: {customer_ids}")
    return fav_number, customer_ids


if __name__ == "__main__":
    my_favorite_function()
