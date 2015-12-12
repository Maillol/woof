from .models import Hotel
from msf.url import EntryPoint


root_url = EntryPoint('/api')


@root_url.get('/hotels')
def get_hotels():
    return Hotel.select()


@root_url.get('/hotels/{hotel_id}', once=True)
def get_hotel(hotel_id):
    return Hotel.select().where(Hotel.id == hotel_id)


@root_url.post('/hotels')
def create_hotel(body):
    return Hotel(**body).save()


@root_url.delete('/hotels/{hotel_id}')
def delete_hotel(hotel_id):
    hotel = list(Hotel.select().where(Hotel.id == hotel_id))[0]
    hotel.delete()
