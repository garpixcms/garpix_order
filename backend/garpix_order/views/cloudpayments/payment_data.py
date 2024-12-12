from django.http import JsonResponse
from ...models import Config
from ...models import CloudPayment


def payment_data_view(request):
    config = Config.get_solo()
    payment_uuid = request.GET.get('payment_uuid')
    try:
        payment = CloudPayment.objects.get(payment_uuid=payment_uuid)
        return JsonResponse({
            'publicId': config.cloudpayments_public_id,
            'description': 'Оплата товара',
            'amount': payment.amount,
            'currency': 'RUB',
            'invoiceId': payment.order_number,
            'skin': "mini",
        })
    except CloudPayment.DoesNotExist:
        return JsonResponse({
            'error': 'Does not exist',
        })
