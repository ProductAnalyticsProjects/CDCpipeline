import random
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text, Identity, Float, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from datetime import datetime, timezone
import itertools

DB_URL = "postgresql://user:password@localhost:1900/inventory"

engine = create_engine(DB_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()
counter = itertools.count()

class Ordini(Base):
    __tablename__ = 'orders'

    id = Column(
        Integer,
        Identity(always=True, start=1, cycle=False),
        primary_key=True
        )
    order_number = Column(String(50))
    amount = Column(Float(10, True, 2))
    tenant_id = Column(Integer)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

def generate_next_order_number():
    with Session() as session:
        max_id = session.query(func.max(Ordini.id)).scalar() or 0
    return max_id + 1

def activity():
    Base.metadata.create_all(engine)

    start_val = generate_next_order_number()
    counter = itertools.count(start=start_val)
    print(f"Inizio generazione da id{start_val}"
          )
    while True:
        next_num = next(counter)
        try:
            with Session() as session:
                action = random.choice(['INSERT', 'INSERT', 'INSERT', 'UPDATE', 'DELETE'])

                if action == 'INSERT':
                    new_order = Ordini(
                        order_number=f'ORD_{next_num}',
                        amount=random.uniform(1.00, 100.00),
                        tenant_id = random.randint(1, 100)
                    )
                    session.add(new_order)
                    print(f"Insert dell'ordine {new_order.order_number}")
                    session.commit()

        except OperationalError as e:
            print(f" Errore di connessione al DB: {e}. Riprovo tra 5 secondi...")
            time.sleep(5)
        except Exception as e:
            print(f"Errore imprevisto: {e}")
            break

if __name__ == "__main__":
    try:
        activity()
    except KeyboardInterrupt:
        print("Fermato dall'utente")
        
