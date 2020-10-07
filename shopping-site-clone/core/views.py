from django.contrib import messages
from django.shortcuts import render, get_object_or_404,redirect
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, Address, UserProfile
from django.views.generic import DetailView,ListView,View
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CheckoutForm, CouponForm,RefundForm, PaymentForm
from django.conf import settings

import string
import random
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

def item_list(request):
    context = {
        'items':Item.objects.all()
    }
    return render(request,"base.html",context)

class HomeView(ListView):
    model = Item
    #paginate_by = 10
    template_name="home.html"

class ShopView(ListView):
    model = Item
    paginate_by = 10
    template_name="shop.html"


class OrderSummaryView(LoginRequiredMixin,View):
    def get(self,*args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user,ordered=False)
            context ={
                'object':order
            }
            return render(self.request,'shopping-cart.html',context)
        except ObjectDoesNotExist:
            messages.warning(self.request,"You do not have an active order.")
            return redirect("/")
        
def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid 

class CheckoutView(View):
    def get(self,*args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user,ordered=False)
            form = CheckoutForm()
            context={
            'form':form,
            'order':order,
            'couponform':CouponForm(),
            'DISPLAY_COUPON_FORM':True
            }

            shipping_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )
            if shipping_address_qs.exists():
                context.update({'default_shipping_address':shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user = self.request.user,
                address_type = 'S',
                default = True
            )
            if billing_address_qs.exists():
                context.update({'default_billing_address':billing_address_qs[0]})    

            return render(self.request,"checkout.html",context)
        except ObjectDoesNotExist:
            messages.info(self.request,"You do not have an active order.")
            return redirect("core:checkout")
        

    def post(self,*args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user,ordered=False)
            if form.is_valid():

                #shipping
                use_default_shipping = form.cleaned_data.get('use_default_shipping')
                if use_default_shipping:
                    print("Using the default shipping address")
                    address_qs = Address.objects.filter(
                    user = self.request.user,
                    address_type = 'S',
                    default = True)

                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(self.request,"No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print('The use is entering a new shipping address')
                    shipping_address1 = form.cleaned_data.get('shipping_address')
                    shipping_address2 = form.cleaned_data.get('shipping_address2')
                    shipping_country = form.cleaned_data.get('shipping_country')
                    shipping_zipcode = form.cleaned_data.get('shipping_zipcode')
                    
                    if is_valid_form([shipping_address1,shipping_country,shipping_zipcode]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address = shipping_address1,
                            apartment_address =  shipping_address2,
                            country = shipping_country,
                            zipcode = shipping_zipcode,
                            address_type = 'S'
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get('set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info(self.request,"Please fill in the required shipping address fields")

                #billing
                use_default_billing = form.cleaned_data.get('use_default_billing')
                same_billing_address = form.cleaned_data.get('same_billing_address')

                if same_billing_address:
                    billing_address = shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the default billing address")
                    address_qs = Address.objects.filter(
                    user = self.request.user,
                    address_type = 'B',
                    default = True)

                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(self.request,"No default billing address available")
                        return redirect('core:checkout')
                else:
                    print('The use is entering a new billing address')
                    billing_address1 = form.cleaned_data.get('billing_address')
                    billing_address2 = form.cleaned_data.get('billing_address2')
                    billing_country = form.cleaned_data.get('billing_country')
                    billing_zipcode = form.cleaned_data.get('billing_zipcode')
                    
                    if is_valid_form([billing_address1,billing_country,billing_zipcode]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address = billing_address1,
                            apartment_address =  billing_address2,
                            country = billing_country,
                            zipcode = billing_zipcode,
                            address_type = 'B'
                        )
                        billing_address.save()
                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get('set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()
                    else:
                        messages.info(self.request,"Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')
                #  implemented redirect to payment option selected
                if payment_option == 'S':
                    return redirect('core:payment',payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment',payment_option='paypal')
                else:
                    messages.warning(self.request,"Invalid Payment Option Selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request,"You do not have an active order.")
            return redirect("core:order-summary")

class PaymentView(View):
    def get(self,*args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order':order,
                # 'DISPLAY_COUPON_FORM':False,
                'STRIPE_PUBLIC_KEY' : settings.STRIPE_PUBLIC_KEY
            }
            userprofile = self.request.user.userprofile
            if userprofile.one_click_purchasing:
                # fetch the users card list
                cards = stripe.Customer.list_sources(
                    userprofile.stripe_customer_id,
                    limit=3,
                    object='card'
                )
                card_list = cards['data']
                if len(card_list) > 0:
                    # update the context with the default card
                    context.update({
                        'card': card_list[0]
                    })
            return render(self.request,"payment.html",context)
        else:
            messages.warning(self.request,"You have not added a billing address.")
            return redirect("core:checkout")
    
    def post(self,*args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = self.request.POST.get('stripeToken')
            
            print(token)
           
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    # customer.sources.create(source=token)
                    stripe.Customer.create(
                        source=token
                    )
                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                        source=token,
                        # name = self.request.user.username,
                        # address = Address.objects.get(user=self.request.user,address_type='S')

                    )
                    # customer.sources.create(source=token)
                    # stripe.Source.create(customer.id, source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.stripe_customer_name = customer['name']
                    userprofile.stripe_customer_address = customer['billing_details']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

        amount=int(order.get_total() * 100)

        try:
            if use_default or save:
                # charge the customer because we cannot charge the token more than once
                charge = stripe.Charge.create(
                amount=amount, #since its in cents
                currency="usd",
                description = 'testing payments',
                customer=userprofile.stripe_customer_id,
                # shipping = {
                #     'name':'userprofile.stripe_customer_name',
                #     'address':'userprofile.stripe_customer_address'
                # }
                )
            else:
                # charge once off on the token
                charge = stripe.Charge.create(
                    amount=amount,  # cents
                    currency="usd",
                    description = 'testing payments',
                    shipping = {
                    'name':'userprofile.stripe_customer_name',
                    'address':'userprofile.stripe_customer_address'
                    },
                    customer=userprofile.stripe_customer_id,
                    source=token
                )


            #create a payment 
            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            #assign payment to the order 

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()
            order.ordered = True
            order.payment = payment
            order.ref_code = create_ref_code()
            order.save()

            messages.success(self.request,"Your order was successful!")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            body = e.json_body
            err = body.get('error',{})
            messages.warning(self.request,f"{err.get('messages')}")
            return redirect("/")
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            messages.warning(self.request,"Rate Limit Error")
            return redirect("/")
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe's API
            messages.warning(self.request,"Invalid Parameters")
            return redirect("/")
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            messages.warning(self.request,"Not Authenticated")
            return redirect("/")
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            messages.warning(self.request,"Network Error")
            return redirect("/")
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            messages.warning(self.request,"Something went wrong. You were not charged. Please try again.")
            return redirect("/")
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            # send email, something wrong in the code
            messages.warning(self.request,"Serious error occured. We have been notified.")
            return redirect("/")



class ItemDetailView(DetailView):
    model = Item
    template_name="product.html"

@login_required
def add_to_cart(request,slug):
    item = get_object_or_404(Item,slug = slug)
    order_item,created = OrderItem.objects.get_or_create(
        item = item,
        user=request.user,
        ordered = False
        )
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]

        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request,"This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request,"This item was added to your cart.")
            order.items.add(order_item)
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date = ordered_date)
        order.items.add(order_item)
        messages.info(request,"This item was added to your cart.")
        return redirect("core:order-summary")

@login_required
def remove_from_cart(request,slug):
    item = get_object_or_404(Item,slug = slug)
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item = item,
                user=request.user,
                ordered = False
            )[0]
            order.items.remove(order_item)
            messages.info(request,"This item was removed to your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request,"This item was not in your cart.")
            return redirect("core:product",slug=slug)
    else:
        messages.info(request,"You do not have an active order.")
        return redirect("core:product",slug=slug)

@login_required
def remove_single_item_from_cart(request,slug):
    item = get_object_or_404(Item,slug = slug)
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item = item,
                user=request.user,
                ordered = False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request,"This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request,"This item was not in your cart.")
            return redirect("core:product",slug=slug)
    else:
        messages.info(request,"You do not have an active order.")
        return redirect("core:product",slug=slug)


def get_coupon(request,code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request,"This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self,*args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(user=self.request.user,ordered=False)
                order.coupon = get_coupon(self.request,code)
                order.save()
                messages.success(self.request,"Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request,"You do not have an active order.")
                return redirect("core:checkout")

class RequestRefundView(View):
    def get(self,*args, **kwargs):
        form = RefundForm()
        context={
            'form':form
        }
        return render(self.request,"request_refund.html",context)

    def post(self,*args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            #edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True 
                order.save()

            #store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()
                messages.info(self.request,"Your request was received")
                return redirect("core:request-refund")
            except ObjectDoesNotExist:
                messages.info(self.request,"This order does not exist")
                return redirect("core:request-refund")