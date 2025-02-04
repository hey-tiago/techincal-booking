from tortoise import fields, models

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

    def model_dump(self, **kwargs) -> dict:
        return {
            "id": self.id,
            "technician_name": self.technician_name,
            "service": self.service,
            "booking_datetime": self.booking_datetime.strftime('%Y-%m-%d %H:%M:%S')
        }
