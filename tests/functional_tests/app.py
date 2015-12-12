import os
import sys
from tempfile import TemporaryDirectory
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from msf.url_parser import path_to_sql
from msf.url import EntryPoint
from msf.db import DataBase
from msf.resource import *
from msf.msf import RESTServer


# models.py
class Book(Resource):
    title = StringField()
    abstract = StringField()
    chapters = ComposedBy('Chapter')

class Chapter(Resource):
    number = IntegerField(weak_id=True)


# controllers.py
root_url = EntryPoint('/api')

@root_url.post('/books')
def create_book(body):
    book = Book(**body)
    book.save()
    return book

@root_url.get('/books')
def get_books():
    return Book.select()

@root_url.get('/books/{book_id}', once=True)
def get_book(book_id):
    return Book.select().where(Book.id == book_id)

@root_url.delete('/books/{book_id}')
def delete_book(book_id):
    book = list(Book.select().where(Book.id == book_id))[0]
    book.delete()

@root_url.post('/books/{book_id}/chapters')
def create_chapter(body, book_id):
    body["book_id"] = book_id
    Chapter(**body).save()

@root_url.get('/books/{book_id}/chapters')
def get_chapters(book_id):
    return Chapter.select().where(Chapter.book_id == book_id)

@root_url.get('/books/{book_id}/chapters/{chapter_id}', once=True)
def get_chapter(book_id):
    return Chapter.select().where(
        (Chapter.book_id == book_id) &
        (Chapter.id == chapter_id))

@root_url.delete('/books/{book_id}/chapters/{chapter_id}')
def delete_chapter(book_id, chapter_id):
    book = list(Chapter.select().where(
        (Chapter.book_id == book_id) &
        (Chapter.id == chapter_id)))[0]
    book.delete()

