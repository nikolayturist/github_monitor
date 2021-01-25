from sqlalchemy import Column, Integer, String, Date, Sequence, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()
engine = create_engine('sqlite:///dto_test.db')


class CarManufacturer(Base):
    __tablename__ = "car_manufacturer"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)


class CarModel(Base):
    __tablename__ = "car_model"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)

    manufacturer_id = Column(Integer, ForeignKey("car_manufacturer.id"))
    manufacturer = relationship("CarManufacturer", back_populates="models")


CarManufacturer.models = relationship("CarModel", order_by=CarModel.id, back_populates="manufacturer")

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine, checkfirst=True)

DBSession = sessionmaker(bind=engine)
db_session = DBSession()

cars = []
cms = []

car1 = CarModel(id=1, name="Toyora Avensis")
cm1 = CarManufacturer(id=1, name="Toyota")
car1.manufacturer_id = cm1.id
car1.manufacturer = cm1

db_session.commit()






car2 = CarModel(id=2, name="Toyora Prius")
car2.manufacturer_id = cm1.id


cm2 = CarManufacturer(id=2, name="VW")
cm2.models.append(CarModel(id=3, name="VW Polo"))
cms.append(cm2)

car3 = CarModel(id=4, name="VW Golf")
cm3 = CarManufacturer(id=2, name="VW")
cm3.models.append(car3)

cms.append(cm3)



# db_session.add_all(cars)
# db_session.add_all(cms)

db_session.commit()
