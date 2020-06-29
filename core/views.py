from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse, HttpRequest
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, View
from django.shortcuts import redirect, render, render_to_response
from django.utils import timezone
from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm, SellerLoginForm, EditItemForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, UserProfile, Category, Seller, VisitProduct,DisplayAds,NotiDisplay
from chartit import DataPool, Chart, PivotDataPool, PivotChart
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.urls import reverse_lazy
from django.template.loader import get_template
from django.db.models.functions import Extract
from graphos.sources.simple import SimpleDataSource
from graphos.renderers import flot, gchart, yui
import random

import random
import string
import stripe
stripe.api_key = 'sk_test_51GGkPGKLvRx6f1cLwi7Gbp8JSUofdV6c8tbeYztY6JUvheBxUw8FiXOGXMDtpl7ZNQjLCw011gvxeeghX6NOApMh00yKobozMR'


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class BestSelling(ListView):
    model = Item
    template_name = "bestseller.html"

    def get_queryset(self, **kwargs):
        queryset = Item.objects.order_by('-count_sold')[:5]
        return queryset

    def render_to_response(self, context, **response_kwargs):

        if not self.request.user.is_anonymous:
            user=self.request.user
            addads = DisplayAds.objects.filter(
                user = user
            )
        else:
            addads = []
        category_id_list = list(Item.objects.values_list('category', flat=True).distinct())
        category_list = Category.objects.filter(pk__in=category_id_list)
        menubar_context = {'category_list': category_list, 'userLogin': not self.request.user.is_anonymous}

        context = {**context, **menubar_context}
        context['advert'] = addads
        context['recom'] = "Recommend"

        if (len(addads) > 0):
            context['advert'] = addads[0]
        template = get_template(context['view'].template_name)
        response = HttpResponse(template.render(context, self.request))

        return response

class PurchaseHistory(ListView):
    model = Item
    paginate_by = 10
    template_name="purchasehistory.html"

    def get_queryset(self, **kwargs):
        itemlist = []
        if not self.request.user.is_anonymous:
            order_list = list(Order.objects.filter(items__isnull=False, payment__isnull=False, user=self.request.user).order_by('-ordered_date'))
            orders = {}
            for x in order_list:
                if(x.pk not in orders):
                    orders[x.pk] = x
            orderlists = list(orders.keys())
            orderlists.sort(reverse=True)
            for x in orderlists:
                allitems = orders[x].items.all()
                for y in allitems:
                    itemlist.append([y,orders[x]])
        return itemlist

    def render_to_response(self, context, **response_kwargs):
        category_id_list = list(Item.objects.values_list('category', flat=True).distinct())
        category_list = Category.objects.filter(pk__in=category_id_list)

        menubar_context = {'category_list': category_list, 'userLogin': not self.request.user.is_anonymous}

        context = {**context, **menubar_context}

        template = get_template(context['view'].template_name)
        response = HttpResponse(template.render(context, self.request))

        return response

def editproduct(request):
    form = EditItemForm(request.POST, request.FILES)
    if request.method == 'POST':
        if form.is_valid():
            title = form.cleaned_data['title']
            price = form.cleaned_data['price']
            discount_price = form.cleaned_data['discount_price']
            category = form.cleaned_data['category']
            label = form.cleaned_data['label']
            slug = form.cleaned_data['slug']
            description = form.cleaned_data['description']
            image = form.cleaned_data['image']
            sellerEmailCookies = request.COOKIES['usmSouvenirShopSeller']
            seller = Seller.objects.get(email=sellerEmailCookies)
            form = Item(title=title, price=price, discount_price=discount_price, category=category, label=label, slug=slug, description=description, image=image, seller=seller)
            form.save()
            return HttpResponseRedirect('/seller/home/')
    sellerEmail = request.COOKIES.get('usmSouvenirShopSeller')
    seller=Seller.objects.filter(email=sellerEmail)
    context = {'form': form}
    context['sellername'] = seller[0].name
    return render(request, 'editproduct.html', context)

def product_update(request, slug, pk, template_name='updateproduct.html'):
    item= get_object_or_404(Item, pk=pk)
    form = EditItemForm(request.POST or None, instance=item)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect('/seller/home/')
    return render(request, template_name, {'form':form})

def product_delete(request, slug, pk, template_name='deleteproduct.html'):
    item= get_object_or_404(Item, pk=pk)
    if request.method=='POST':
        item.delete()
        return HttpResponseRedirect('/seller/home/')
    return render(request, template_name, {'object':item})

class SellerHome(ListView):
    template_name = 'sellerhome.html'
    model = Item
    paginate_by = 10
    context_object_name ='sellerhome'
    def get_queryset(self):
        sellerEmail = self.request.COOKIES.get('usmSouvenirShopSeller')
        seller=Seller.objects.filter(email=sellerEmail)
        return Item.objects.filter(seller=seller[0])
    def render_to_response(self, context, **response_kwargs):
        context={**context}
        sellerEmail = self.request.COOKIES.get('usmSouvenirShopSeller')
        seller=Seller.objects.filter(email=sellerEmail)
        context['sellername'] = seller[0].name
        template = get_template(context['view'].template_name)
        response = HttpResponse(template.render(context, self.request))
        return response

def sales(request):
    print("Sales Report")
    sellerEmailCookies = request.COOKIES['usmSouvenirShopSeller']
    seller = list(Seller.objects.filter(email=sellerEmailCookies).values_list('pk', flat=True))
    item_list = list(Item.objects.filter(seller=seller[0]).values_list('pk', flat=True))
    order_item_list = [list(OrderItem.objects.filter(item=item).values_list('pk', flat=True)) for item in
                              item_list]
    # may without payment
    order_item_list = [num for elem in order_item_list for num in elem]
    # may contain other seller item
    order_list = [list(Order.objects.filter(items__isnull=False, payment__isnull=False, items=items).values_list('pk', 'items')) for items in order_item_list]
    order_list = [num for elem in order_list for num in elem]

    order_items_list=[]
    order_items_order_id=[]
    # order_list
    for i in range(len(order_list)):
        order_pk = order_list[i][0]
        order_items = order_list[i][1]
        if order_items in order_item_list:
            # order item with payment and seller
            order_items_list.append(list(OrderItem.objects.filter(pk=order_items)))
            # order id with payment and seller
            order_items_order_id.append(order_pk)

    month_sales_list=[]
    month_sales_list.append(['Month','Amount(RM)'])
    category_sales_list = []
    category_sales_list.append(['Category', 'Sales'])
    monthdict = {
        'January' :1, 
        'February':2, 
        'March':3, 
        'April':4, 
        'May':5, 
        'June':6, 
        'July':7, 
        'August':8, 
        'September':9, 
        'October':10, 
        'November':11, 
        'December':12
    }
    for i in range(len(order_items_list)):
        order_pk=order_items_order_id[i]
        order_item_pk=order_items_list[i][0].pk
        quantity=order_items_list[i][0].quantity
        ordersales = order_items_list[i][0].get_total_item_price()
        category=order_items_list[i][0].item.category.name
        month=Order.objects.filter(items__isnull=False, payment__isnull=False,pk=order_pk, items=order_item_pk).order_by('ordered_date').values_list('ordered_date')[0][0].strftime('%B')
        month_sales=[monthdict[month], ordersales]
        category_sales=[category,quantity]
        month_sales_list.append(month_sales)
        category_sales_list.append(category_sales)
    month_data_list=[]
    temp_moth_list = []
    for i in range(len(month_sales_list)):
        contain = False
        if len(month_data_list)==0:
            month_data_list.append(month_sales_list[i])
        else:
            for j in range(len(temp_moth_list)):
                if month_sales_list[i][0]==temp_moth_list[j][0]:
                    temp_moth_list[j][1]=temp_moth_list[j][1]+month_sales_list[i][1]
                    contain=True
            if contain==False:
                temp_moth_list.append(month_sales_list[i])
    temp_moth_list.sort()
    monthkey = list(monthdict.keys())
    for x in temp_moth_list:
        newx = [monthkey[x[0]-1],x[1]]
        month_data_list.append(newx)

    category_data_list = []
    for i in range(len(category_sales_list)):
        contain = False
        if len(category_data_list) == 0:
            category_data_list.append(category_sales_list[i])
        else:
            for j in range(len(category_data_list)):
                if category_sales_list[i][0] == category_data_list[j][0]:
                    category_data_list[j][1] = category_data_list[j][1] + category_sales_list[i][1]
                    contain = True
            if contain == False:
                category_data_list.append(category_sales_list[i])

    # Chart object
    chart = gchart.BarChart(SimpleDataSource(data=month_data_list), options={'title': 'Sales 2020 by Months'})
    pie_chart = gchart.PieChart(SimpleDataSource(data=category_data_list), options={'title': 'Sales 2020 by Category (Sale Units)'})

    context = {
        'chart': chart,
        'pie_chart': pie_chart
    }
    seller=Seller.objects.filter(email=sellerEmailCookies)
    context['sellername'] = seller[0].name
    return render(request, 'salesreport.html', context)

class Notification(ListView):
    model = Item
    paginate_by = 10
    template_name = "notification.html"
    def get_context_data(self, **kwargs):
        sellerEmailCookies = self.request.COOKIES['usmSouvenirShopSeller']
        seller = list(Seller.objects.filter(email=sellerEmailCookies).values_list('pk', flat=True))
        #item_list contains item of each seller
        item_list = list(Item.objects.filter(seller=seller[0]).values_list('pk', flat=True))
        order_item_list = [list(OrderItem.objects.filter(item=item).values_list('pk', flat=True)) for item in
                                item_list]
        # may without payment
        order_item_list = [num for elem in order_item_list for num in elem]

        # may contain other seller item
        order_list = [list(Order.objects.filter(items__isnull=False, payment__isnull=False, items=items).values_list('pk', 'items')) for items in order_item_list]

        order_list = [num for elem in order_list for num in elem]

        order_items_list=[]
        order_items_order_id=[]
        # order_list
        
        for i in range(len(order_list)):
            order_pk = order_list[i][0]
            order_items = order_list[i][1]
            if order_items in order_item_list:
                # order item with payment and seller
                order_items_list.append(list(OrderItem.objects.filter(pk=order_items)))
                
                # order id with payment and seller
                order_items_order_id.append(order_pk)
        finallist = []
        totaldict = {}
        orderlist = []
        for x in range(0,len(order_items_list)):
            finallist.append([order_items_order_id[x],order_items_list[x][0]]) 
            
            if(order_items_order_id[x] not in totaldict):
                orderlist.append(order_items_order_id[x])
                total = order_items_list[x][0].quantity * order_items_list[x][0].item.price
                totaldict[order_items_order_id[x]] = total
            else:
                total = totaldict[order_items_order_id[x]]
                total += order_items_list[x][0].quantity * order_items_list[x][0].item.price
                totaldict[order_items_order_id[x]] = total
        
        
        orderlist.sort(reverse = True)
        orderslist = []
        for x in range(0,len(orderlist)):
            possOrders = Order.objects.filter(
                pk = orderlist[x]
            )
            orderslist.append(possOrders[0])
        context = {
            'orderlist': orderslist
        }
        seller=Seller.objects.filter(email=sellerEmailCookies)
        context['sellername'] = seller[0].name
        return context

class NotificationReceipt(View):
    def get(self,request,**kwargs):
        print("NotificationRecceipt")
        orderid = kwargs['id']
        sellerEmailCookies = self.request.COOKIES['usmSouvenirShopSeller']
        seller = list(Seller.objects.filter(email=sellerEmailCookies).values_list('pk', flat=True))
        #item_list contains item of each seller
        item_list = list(Item.objects.filter(seller=seller[0]).values_list('pk', flat=True))
        order_item_list = [list(OrderItem.objects.filter(item=item).values_list('pk', flat=True)) for item in
                                item_list]
        # may without payment
        order_item_list = [num for elem in order_item_list for num in elem]

        # may contain other seller item
        order_list = [list(Order.objects.filter(items__isnull=False, payment__isnull=False, items=items).values_list('pk', 'items')) for items in order_item_list]
        
        order_list = [num for elem in order_list for num in elem]

        order_items_list=[]
        order_items_order_id=[]
        # order_list
        for i in range(len(order_list)):
            order_pk = order_list[i][0]
            order_items = order_list[i][1]
            if order_items in order_item_list:
                # order item with payment and seller
                order_items_list.append(list(OrderItem.objects.filter(pk=order_items)))
                
                # order id with payment and seller
                order_items_order_id.append(order_pk)
        
        finallist = []
        totaldict = {}
        orderlist = []
        for x in range(0,len(order_items_list)):
            finallist.append([order_items_order_id[x],order_items_list[x][0]]) 
            
            if(order_items_order_id[x] not in totaldict):
                orderlist.append(order_items_order_id[x])
                total = order_items_list[x][0].quantity * order_items_list[x][0].item.price
                totaldict[order_items_order_id[x]] = total
            else:
                total = totaldict[order_items_order_id[x]]
                total += order_items_list[x][0].quantity * order_items_list[x][0].item.price
                totaldict[order_items_order_id[x]] = total
        
        orderlist.sort(reverse = True)
        orderitems = []
        customer = None
        totalprice = totaldict[int(orderid)]
        date = Order.objects.filter(pk=orderid)
        purchasedate = date[0].payment.timestamp
        address = date[0].shipping_address.get_full_address()
        postcode = date[0].shipping_address.zip
        customer = date[0].user
        
        for x in range(0,len(finallist)):
            if(finallist[x][0] == int(orderid)):
                orderitems.append(finallist[x][1])
        context = {
            'orderlist' : orderitems,
            'orderids' : orderid,
            'cust' : customer,
            'email': customer.email,
            'address': address,
            'postcode': postcode,
            'date' : purchasedate,
            'total' : totalprice
        }
        seller=Seller.objects.filter(email=sellerEmailCookies)
        context['sellername'] = seller[0].name
        return render(request,'notificationreceipt.html',context)

def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)

def category(request,hierarchy= None):
    category_slug = hierarchy.split('/')
    category_queryset = list(Category.objects.all())

    all_slugs = [ x.slug for x in category_queryset ]
    parent = None
    for slug in category_slug:
        if slug in all_slugs:
            parent = get_object_or_404(Category,slug=slug,parent=parent)
        else:
            instance = get_object_or_404(Post, slug=slug)
            breadcrumbs_link = instance.get_cat_list()
            category_name = [' '.join(i.split('/')[-1].split('-')) for i in breadcrumbs_link]
            breadcrumbs = zip(breadcrumbs_link, category_name)
            return render(request, "home.html", {'instance':instance,'breadcrumbs':breadcrumbs})

    category_id_list=list(Item.objects.values_list('category', flat=True).distinct())
    category_list=Category.objects.filter(pk__in=category_id_list)
    if not request.user.is_anonymous:
        user = request.user
        addads = DisplayAds.objects.filter(
            user=user
        )
    else:
        addads = []

    context = {
        'item_set':parent.item_set.all(),
        'sub_categories':parent.children.all(),
        'category_list':category_list,
        'userLogin': not request.user.is_anonymous,
        'advert' : addads,
        'recom':"Recommend"
    }

    if (len(addads) > 0):
        context['advert'] = addads[0]

    return render(request,"category.html",context)

def seller_login(request):
    context = {
        'error': 0
    }
    if request.method == 'POST':
        try:
            instance=Seller.objects.get(email=request.POST.get('seller_email'))
            if request.POST.get('seller_email').strip()==instance.email and request.POST.get('seller_password').strip()==instance.password:
                response = HttpResponseRedirect('/seller/home/')
                response.set_cookie('usmSouvenirShopSeller', request.POST.get('seller_email').strip())
                return response
            else:
                context = {
                    'error': 1
                }
        except ObjectDoesNotExist:
            context = {
                'error': 1
            }
            return render(request, "sellerlogin.html", context)
    return render(request, "sellerlogin.html", context)

def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid

class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }

            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            billing_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='B',
                default=True
            )
            if billing_address_qs.exists():
                context.update(
                    {'default_billing_address': billing_address_qs[0]})

            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():

                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')

                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                            address_type='S'
                        )
                        shipping_address.save()

                        order.shipping_address = shipping_address
                        order.save()

                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")

                use_default_billing = form.cleaned_data.get(
                    'use_default_billing')
                same_billing_address = form.cleaned_data.get(
                    'same_billing_address')

                if same_billing_address:
                    billing_address = order.shipping_address
                    billing_address.pk = None
                    billing_address.save()
                    billing_address.address_type = 'B'
                    billing_address.save()
                    order.billing_address = billing_address
                    order.save()

                elif use_default_billing:
                    print("Using the defualt billing address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='B',
                        default=True
                    )
                    if address_qs.exists():
                        billing_address = address_qs[0]
                        order.billing_address = billing_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default billing address available")
                        return redirect('core:checkout')
                else:
                    print("User is entering a new billing address")
                    billing_address1 = form.cleaned_data.get(
                        'billing_address')
                    billing_address2 = form.cleaned_data.get(
                        'billing_address2')
                    billing_country = form.cleaned_data.get(
                        'billing_country')
                    billing_zip = form.cleaned_data.get('billing_zip')

                    if is_valid_form([billing_address1, billing_country, billing_zip]):
                        billing_address = Address(
                            user=self.request.user,
                            street_address=billing_address1,
                            apartment_address=billing_address2,
                            country=billing_country,
                            zip=billing_zip,
                            address_type='B'
                        )
                        billing_address.save()

                        order.billing_address = billing_address
                        order.save()

                        set_default_billing = form.cleaned_data.get(
                            'set_default_billing')
                        if set_default_billing:
                            billing_address.default = True
                            billing_address.save()

                    else:
                        messages.info(
                            self.request, "Please fill in the required billing address fields")

                payment_option = form.cleaned_data.get('payment_option')

                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")

class PaymentView(View):
    paginate_by = 10
    template_name = "payment.html"
    def get(self, *args, **kwargs):
        print("get")
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                'order': order,
                'DISPLAY_COUPON_FORM': False
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
            print("end get")
            return render(self.request, "payment.html", context)
        else:
            messages.warning(
                self.request, "You have not added a billing address")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        print("post")
        order = Order.objects.get(user=self.request.user, ordered=False)
        form = PaymentForm(self.request.POST)
        userprofile = UserProfile.objects.get(user=self.request.user)
        if form.is_valid():
            token = form.cleaned_data.get('stripeToken')
            save = form.cleaned_data.get('save')
            use_default = form.cleaned_data.get('use_default')

            if save:
                if userprofile.stripe_customer_id != '' and userprofile.stripe_customer_id is not None:
                    customer = stripe.Customer.retrieve(
                        userprofile.stripe_customer_id)
                    customer.sources.create(source=token)

                else:
                    customer = stripe.Customer.create(
                        email=self.request.user.email,
                        name=self.request.user.username,
                    )
                    customer.sources.create(source=token)
                    userprofile.stripe_customer_id = customer['id']
                    userprofile.one_click_purchasing = True
                    userprofile.save()

            amount = int(order.get_total() * 100)

            try:
                if use_default or save:
                    # charge the customer because we cannot charge the token more than once
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="myr",
                        description=order.items.all(),
                        customer=userprofile.stripe_customer_id
                    )
                else:
                    # charge once off on the token
                    charge = stripe.Charge.create(
                        amount=amount,  # cents
                        currency="myr",
                        source=token,
                        description = order.items.all(),
                    )

                # create the payment
                payment = Payment()
                payment.stripe_charge_id = charge['id']
                payment.user = self.request.user
                payment.amount = order.get_total()
                payment.save()

                # assign the payment to the order

                order_items = order.items.all()
                order_items.update(ordered=True)
                for item in order_items:
                    item.save()

                order.ordered = True
                order.payment = payment
                order.ref_code = create_ref_code()
                order.save()

                bought = []
                itembought = {}
                for x in order_items:
                    item = x.item
                    cate = item.category
                    bought.append(item.title)
                    if(cate in itembought):
                        itembought[cate] +=1
                    else:
                        itembought[cate] = 1
                max = 0
                recommendcate = ''
                for x,y in itembought.items():
                    if(y > max):
                        max = y
                        recommendcate = x
                itemcate = None
                for x in order_items:
                    if(x.item.category == recommendcate):
                        itemcate = x.item.category
                itemlist_qs = Item.objects.filter(
                    category = itemcate
                )
                allitem = []
                for x in itemlist_qs:
                    allitem.append(x.title)
                finalList = [x for x in allitem if x not in bought]
                recommenditem = ''
                if(len(finalList) >0):
                    recommenditem = random.choice(finalList)
                else:
                    recommenditem = random.choice(allitem)
                item_qs = Item.objects.filter(
                    title = recommenditem
                )
                addads = DisplayAds(
                    user = self.request.user,
                    item = item_qs[0]
                )
                addads.save()
                context = {
                    'advert':addads,
                    'recom':"Recommend",
                    'object_list' : Item.objects.all()
                }

                category_id_list = list(Item.objects.values_list('category', flat=True).distinct())
                category_list = Category.objects.filter(pk__in=category_id_list)
                context = {
                    'advert': addads,
                    'recom': "Recommend",
                    'object_list': Item.objects.all(),
                    'category_list': category_list,
                    'userLogin': not self.request.user.is_anonymous
                }

                if not self.request.user.is_anonymous:
                    user = self.request.user
                    allads = list(DisplayAds.objects.filter(user=user).all().values_list('item', flat=True).distinct())
                else:
                    allads = []
                allads = Item.objects.filter(pk__in=allads)
                if (len(allads) > 3):
                    context['recommend_list'] = allads[:3]
                else:
                    context['recommend_list'] = allads

                messages.success(self.request, "Your order was successful!")
                stripe.Customer.create(
                    email = self.request.user.email,
                    customer = self.request.user.userprofile,
                    description = order.items.all()



                )
                print("end post")
                return render(self.request, "home.html", context)
                #return redirect("/")

            except stripe.error.CardError as e:
                body = e.json_body
                err = body.get('error', {})
                messages.warning(self.request, f"{err.get('message')}")
                return redirect("/")

            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                messages.warning(self.request, "Rate limit error")
                return redirect("/")

            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API

                print(e)
                messages.warning(self.request, "Invalid parameters")
                return redirect("/")

            except stripe.error.AuthenticationError as e:
                print(e)
                # Authentication with Stripe's API failed
                # (maybe you changed API keys recently)
                messages.warning(self.request, "Not authenticated")
                return redirect("/")

            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                messages.warning(self.request, "Network error")
                return redirect("/")

            except stripe.error.StripeError as e:
                # Display a very generic error to the user, and maybe send
                # yourself an email
                messages.warning(
                    self.request, "Something went wrong. You were not charged. Please try again.")
                return redirect("/")

            except Exception as e:
                # send an email to ourselves
                messages.warning(
                    self.request, "A serious error occurred. We have been notified.")
                return redirect("/")

        messages.warning(self.request, "Invalid data received")
        return redirect("/payment/stripe/")

class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"

    def render_to_response(self, context, **response_kwargs):
        category_id_list = list(Item.objects.values_list('category', flat=True).distinct())
        category_list = Category.objects.filter(pk__in=category_id_list)
        menubar_context = {'category_list': category_list, 'userLogin': not self.request.user.is_anonymous}
        if not self.request.user.is_anonymous:
            user=self.request.user
            allads = list(DisplayAds.objects.filter(user = user).all().values_list('item', flat=True).distinct())
        else:
            allads = []
        allads = Item.objects.filter(pk__in=allads)
        context={**context, **menubar_context}
        if(len(allads) > 0):
            context['advert'] = allads[0]
            if (len(allads) > 3):
                context['recommend_list'] = allads[:3]
            else:
                context['recommend_list'] = allads
            context['recom'] = "Recommend"
        template = get_template(context['view'].template_name)
        response = HttpResponse(template.render(context, self.request))
        return response

class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {
                'object': order
            }
            return render(self.request, 'order_summary.html', context)
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("/")

class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tempcookie = self.request.COOKIES.get('adstop', 'default')
        tempsessionid = self.request.COOKIES.get('sessionid')
        currvisitItem = context['item']
        if self.request.user.is_authenticated and (not self.request.user.is_staff )and (not self.request.user.is_superuser):
            find_session_qs = VisitProduct.objects.filter(
                sessionid = tempsessionid
            )
            if find_session_qs.exists():
                uservisit = VisitProduct(
                    sessionid = tempsessionid,
                    visitnum = find_session_qs[len(find_session_qs)-1].visitnum +1,
                    productname = currvisitItem.title,
                    productcategory = currvisitItem.category
                )
                uservisit.save()
            else:
                uservisit = VisitProduct(
                    sessionid = tempsessionid,
                    visitnum = 1,
                    productname = currvisitItem.title,
                    productcategory = currvisitItem.category
                )
                uservisit.save()
            if(tempcookie == 'default'):
                curr_session_qs = VisitProduct.objects.filter(
                    sessionid = tempsessionid
                )
                currVisited = []
                for x in curr_session_qs:
                    currVisited.append(x.productname)
                visitlength = curr_session_qs[len(curr_session_qs)-1].visitnum
                visittarget = visitlength+1
                if(visitlength >3):
                    target_qs = VisitProduct.objects.filter(
                        visitnum = visittarget
                    )
                    targets = []
                    recommenditem = None
                    if(len(target_qs)>0):
                        for x in target_qs:
                            targets.append(x.sessionid)
                        recommenditem = self.recommendtaion(visitlength,targets,currVisited)

                    if(recommenditem != None):
                        item_qs = Item.objects.filter(
                            title = recommenditem
                        )
                        addads = DisplayAds(
                            sessionid = tempsessionid,
                            item = item_qs[0]
                        )
                        addads.save()
                        context['advert'] = addads
                        context['recom'] = "Recommend"

        #Botton recommendation list start
        similarlist = []
        similarItems = Item.objects.filter(
            category = currvisitItem.category
        )
        count = 0
        adslimit = 0

        availen = len(similarItems)

        while(adslimit <4 and count < availen):
            if(similarItems[count].title != currvisitItem.title):
                similarlist.append(similarItems[count])
                adslimit+=1
            count+=1
        context['similar'] = similarlist
        #Botton recommendation list end
        return context
    

    def recommendtaion(self,currVisitNo,targets,currVisits):
        print("Recommendation")
        
        targetitem = []
        for x in targets:
            prodlist = []
            prod_qs = VisitProduct.objects.filter(
                sessionid = x
            )
            for y in prod_qs:
                prodlist.append(y.productname)
            if(len(prodlist) > len(currVisits) and prodlist[:currVisitNo] == currVisits):
                print("success")
                targetitem.append(prodlist[currVisitNo])
       
        if len(targetitem)>0:
            print("Done")
            return targetitem[len(targetitem)-1]
        print("Failed")
        return None

    def render_to_response(self, context, **response_kwargs):
        template = get_template(context['view'].template_name)
        response = HttpResponse(template.render(context, self.request))
        response.set_cookie('adstop', 'Alive',max_age=0)
        return response

class ItemEditView(DetailView):
    model = Item
    template_name = "editsingleproduct.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sellerEmailCookies = self.request.COOKIES.get('usmSouvenirShopSeller')
        context['sellerEmail'] = sellerEmailCookies
        return context

@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")
