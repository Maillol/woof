import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from msf.url import EntryPoint
from msf.resource import *


# models.py
class Book(Resource):
    title = StringField()
    abstract = StringField()
    chapters = ComposedBy('Chapter')

class Chapter(Resource):
    number = IntegerField(weak_id=True)


# controllers.py
root_url = EntryPoint('/api')
root_url.crud('/books/[id]', Book)


@root_url.post('/books/{book_id}/chapters')
def create_chapter(body, book_id):
    body["book_id"] = book_id
    Chapter(**body).save()


@root_url.get('/books/{book_id}/chapters')
def get_chapters(book_id):
    return Chapter.select().where(Chapter.book_id == book_id)


@root_url.get('/books/{book_id}/chapters/{chapter_id}', single=True)
def get_chapter(book_id, chapter_id):
    return Chapter.select().where(
        (Chapter.book_id == book_id) &
        (Chapter.id == chapter_id))


@root_url.delete('/books/{book_id}/chapters/{chapter_id}')
def delete_chapter(book_id, chapter_id):
    book = list(Chapter.select().where(
        (Chapter.book_id == book_id) &
        (Chapter.id == chapter_id)))[0]
    book.delete()

