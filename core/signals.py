import os
from django.db.models.signals import pre_delete
from django.dispatch import receiver


def delete_file_model(model_name, name_field="image"):

    @receiver(pre_delete, sender=model_name)
    def delete_image(sender, instance, **kwargs):
        attr = getattr(instance, name_field, None)
        if attr:
            try:
                if os.path.isfile(attr.path):
                    os.remove(attr.path)
            except Exception as e:
                print(f"Error Deleted {name_field}: {e}")