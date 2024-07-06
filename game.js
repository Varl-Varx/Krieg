let socket = io();
let stripe = Stripe('your_stripe_public_key');
let userId;

async function register() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const response = await axios.post('/register', { email, password });
    alert(response.data.message);
}

async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const response = await axios.post('/login', { email, password });
    if (response.data.message === 'Login successful') {
        userId = response.data.user_id;
        document.getElementById('loginContainer').style.display = 'none';
        document.getElementById('gameInterface').style.display = 'block';
        fetchCountryInfo();
    } else {
        alert(response.data.message);
    }
}

async function fetchCountryInfo() {
    const response = await axios.get('/api/countries');
    const countries = response.data;
    updateCountryInfo(countries);
}

function updateCountry
