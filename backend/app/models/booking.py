from tortoise import fields, models
from datetime import datetime

class Booking(models.Model):
    id = fields.IntField(pk=True)
    technician_name = fields.CharField(max_length=100)
    service = fields.CharField(max_length=100)
    booking_datetime = fields.DatetimeField()
    user = fields.ForeignKeyField("models.User", related_name="bookings", null=True)

    def __str__(self):
        return (
            f"Booking(id={self.id}, technician={self.technician_name}, "
            f"service={self.service}, datetime={self.booking_datetime})"
        )

    class Meta:
        table = "booking" 