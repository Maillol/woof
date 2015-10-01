from resource2 import *
from msf import RESTServer
import peewee

class Lieu(Resource):
    name = StringField()

class Trajet(Resource):
    name = StringField(str)
    dep = ResourceField('Lieu', related_name='trajet_dep_set')
    arr = ResourceField('Lieu', related_name='trajet_arr_set')

MetaResource._name_to_ref()
MetaResource._initialize_db(peewee.SqliteDatabase('test2.db'))
MetaResource.db.connect()

if not "create table":
    Lieu = MetaResource.register['Lieu'][0]
    Trajet = MetaResource.register['Trajet'][0]

    MetaResource.db.create_tables([Lieu, Trajet])
    with MetaResource.db.atomic():
        paris = Lieu.create(name="Paris")
        besancon = Lieu.create(name="Besancon")
        mtp = Lieu.create(name="Montpellier")
        Trajet.create(name="P -> B", dep=paris, arr=besancon)
        Trajet.create(name="P -> M", dep=paris, arr=mtp)

if "server":
    application = RESTServer()

else:
    Lieu = MetaResource.register['Lieu'][0]
    Trajet = MetaResource.register['Trajet'][0]

    with MetaResource.db.atomic():
        from pprint import pprint
        print('°' * 32)
        q = Trajet.select().where(Trajet.id == 1).join(Lieu, on=Lieu.id == Trajet.dep).where(Lieu.id==1)
        #url = '/Lieu-dep/1/Trajet/'
        url = '/Monde/3/Lieu-dep/1/Trajet/'
        paris = Lieu.select().where(Lieu.name=='Paris').get()

        #Trajet.create(dep=Lieu.select().where(Lieu.name=='Montpellier'), name="Pieton", arr=paris)
        
        #print(Trajet.select().where(Trajet.name=="Pieton").get().dep.name)

        #url = '/Lieu/0'

        print(url)
        #print('ICI', MetaResource.db.interpolation)

