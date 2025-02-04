from tortoise import fields, models
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .booking import Booking

class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    hashed_password = fields.CharField(max_length=128)
    bookings: fields.ReverseRelation["Booking"]

    def __str__(self):
        return self.username