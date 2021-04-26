#from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from .forms import CustomSignupForm
from django.urls import reverse_lazy
from django.views import generic
from .models import CourseHero , Customer
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
import stripe
from django.http import HttpResponse

stripe.api_key = "sk_test_IypT2bqOfu6h6xTFVr0uMfX400ziXYWvkw"


def index(request):
    return HttpResponse("Welcome to our Membership website")

def home(request):
    plans = CourseHero.objects
    return render(request, 'courses/home.html', {'plans':plans})

def plan(request,pk):
    plan = get_object_or_404(CourseHero, pk=pk)
    if plan.premium :
        if request.user.is_authenticated:
            try:
                if request.user.customer.membership:
                    return render(request, 'courses/plan.html', {'plan':plan})
            except Customer.DoesNotExist:
                    return redirect('join')
        return redirect('join')
    else:
        return render(request, 'courses/plan.html', {'plan':plan})

def join(request):
    return render(request, 'courses/join.html')

@login_required
def checkout(request):

    try:
        if request.user.customer.membership:
            return redirect('settings')
    except Customer.DoesNotExist:
        pass

    coupons = {'christmas':31, 'welcome':10}

    if request.method == 'POST':
        stripe_customer = stripe.Customer.create(email=request.user.email, source=request.POST['stripeToken'])
        plan = 'price_1IhW37C4G22E1tTDA5Z5v4ij'
        if request.POST['plan'] == 'yearly':
            plan = 'price_1IhW90C4G22E1tTDkM2DTALW'
        if request.POST['coupon'] in coupons:
            percentage = coupons[request.POST['coupon'].lower()]
            try:
                coupon = stripe.Coupon.create(duration='once', id=request.POST['coupon'].lower(),
                percent_off=percentage)
            except:
                pass
            subscription = stripe.Subscription.create(customer=stripe_customer.id,
            items=[{'plan':plan}], coupon=request.POST['coupon'].lower())
        else:
            subscription = stripe.Subscription.create(customer=stripe_customer.id,
            items=[{'plan':plan}])

        customer = Customer()
        customer.user = request.user
        customer.stripeid = stripe_customer.id
        customer.membership = True
        customer.cancel_at_period_end = False
        customer.stripe_subscription_id = subscription.id
        customer.save()

        return redirect('home')
    else:
        coupon = 'none'
        plan = 'monthly'
        price = 2000
        og_dollar = 20
        coupon_dollar = 0
        final_dollar = 20
        if request.method == 'GET' and 'plan' in request.GET:
            if request.GET['plan'] == 'yearly':
                plan = 'yearly'
                price = 20000
                og_dollar = 200
                final_dollar = 200
        if request.method == 'GET' and 'coupon' in request.GET:
            print(coupons)
            if request.GET['coupon'].lower() in coupons:
                print('fam')
                coupon = request.GET['coupon'].lower()
                percentage = coupons[request.GET['coupon'].lower()]


                coupon_price = int((percentage / 100) * price)
                price = price - coupon_price
                coupon_dollar = str(coupon_price)[:-2] + '.' + str(coupon_price)[-2:]
                final_dollar = str(price)[:-2] + '.' + str(price)[-2:]

        return render(request, 'courses/checkout.html',
        {'plan':plan,'coupon':coupon,'price':price,'og_dollar':og_dollar,
        'coupon_dollar':coupon_dollar,'final_dollar':final_dollar})

def settings(request):
    membership = False
    cancel_at_period_end = False
    if request.method == 'POST':
        subscription = stripe.Subscription.retrieve(request.user.customer.stripe_subscription_id)
        subscription.cancel_at_period_end = True
        request.user.customer.cancel_at_period_end = True
        cancel_at_period_end = True
        subscription.save()
        request.user.customer.save()
    else:
        try:
            if request.user.customer.membership:
                membership = True
            if request.user.customer.cancel_at_period_end:
                cancel_at_period_end = True
        except Customer.DoesNotExist:
            membership = False
    return render(request, 'registration/settings.html', {'membership':membership,
    'cancel_at_period_end':cancel_at_period_end})

@user_passes_test(lambda u: u.is_superuser)
def updateaccounts(request):
    customers = Customer.objects.all()
    for customer in customers:
        subscription = stripe.Subscription.retrieve(customer.stripe_subscription_id)
        if subscription.status != 'active':
            customer.membership = False
        else:
            customer.membership = True
        customer.cancel_at_period_end = subscription.cancel_at_period_end
        customer.save()
    return HttpResponse('completed')

class SignUp(generic.CreateView):
    form_class = CustomSignupForm
    success_url = reverse_lazy('home')
    template_name = 'registration/register.html'

    def form_valid(self, form):
        valid = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get('username'), form.cleaned_data.get('password1')
        new_user = authenticate(username=username, password=password)
        login(self.request, new_user)
        return valid
