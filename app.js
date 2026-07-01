const tg = window.Telegram.WebApp;
tg.expand();

const scoreEl = document.getElementById('score');
const clickBtn = document.getElementById('click-btn');
const usernameEl = document.getElementById('username');

// Элементы навигации
const navGame = document.getElementById('nav-game');
const navShop = document.getElementById('nav-shop');
const navLeaderboard = document.getElementById('nav-leaderboard');

const gameScreen = document.getElementById('game-screen');
const shopScreen = document.getElementById('shop-screen');
const leaderboardScreen = document.getElementById('leaderboard-screen');
const leadersListEl = document.getElementById('leaders-list');

// Элементы магазина
const buyClickBtn = document.getElementById('buy-click-btn');
const clickLevelDesc = document.getElementById('click-level-desc');

let userId = "local_user";
let username = "Локальный Тестер";
let score = 0;

let clickLevel = 1;
let clickPower = 1;
let upgradeCost = 100;

const BACKEND_URL = "https://neon-clicker-backend.onrender.com";

if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
    const user = tg.initDataUnsafe.user;
    userId = user.id.toString();
    username = user.username ? `@${user.username}` : user.first_name;
    usernameEl.innerText = username;
} else {
    usernameEl.innerText = username;
}

function resetScreens() {
    navGame.classList.remove('active');
    navShop.classList.remove('active');
    navLeaderboard.classList.remove('active');
    
    gameScreen.classList.remove('active-screen');
    shopScreen.classList.remove('active-screen');
    leaderboardScreen.classList.remove('active-screen');
}

// Навигация
navGame.addEventListener('click', () => {
    resetScreens();
    navGame.classList.add('active');
    gameScreen.classList.add('active-screen');
});

navShop.addEventListener('click', () => {
    resetScreens();
    navShop.classList.add('active');
    shopScreen.classList.add('active-screen');
});

navLeaderboard.addEventListener('click', () => {
    resetScreens();
    navLeaderboard.classList.add('active');
    leaderboardScreen.classList.add('active-screen');
    loadLeaderboard();
});

// Загрузка данных (исправленная версия, которая будит сервер)
async function loadUserData() {
    try {
        const resCheck = await fetch(`${BACKEND_URL}/get_balance?user_id=${userId}`);
        
        if (resCheck.ok) {
            const data = await resCheck.json();
            
            score = data.balance || 0;
            clickLevel = data.click_level || 1;
            clickPower = data.click_power || 1;
            
            upgradeCost = 100;
            for (let i = 1; i < clickLevel; i++) {
                upgradeCost = Math.round(upgradeCost * 2.5);
            }

            scoreEl.innerText = score;
            updateShopUI();
        } else {
            await fetch(`${BACKEND_URL}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, username: username, clicks: 0 })
            });
            setTimeout(loadUserData, 1000);
        }
    } catch (e) {
        console.error("Ошибка загрузки данных, пробуем еще раз...", e);
        setTimeout(loadUserData, 3000);
    }
}

// Загрузка таблицы лидеров
async function loadLeaderboard() {
    try {
        leadersListEl.innerHTML = "<div style='text-align:center; color:#8a8a8a;'>Загрузка топа...</div>";
        const response = await fetch(`${BACKEND_URL}/get_leaders`);
        const leaders = await response.json();
        
        leadersListEl.innerHTML = "";
        
        leaders.forEach((player, index) => {
            const place = index + 1;
            let topClass = "";
            let medal = `${place}`;
            
            if (place === 1) { topClass = "top-1"; medal = "🥇"; }
            else if (place === 2) { topClass = "top-2"; medal = "🥈"; }
            else if (place === 3) { topClass = "top-3"; medal = "🥉"; }
            
            const item = document.createElement('div');
            item.className = `leader-item ${topClass}`;
            item.innerHTML = `
                <div class="leader-info">
                    <span class="place-badge">${medal}</span>
                    <span class="leader-name">${player.username}</span>
                </div>
                <span class="leader-score">${player.balance} 💰</span>
            `;
            leadersListEl.appendChild(item);
        });
    } catch (e) {
        leadersListEl.innerHTML = "<div style='text-align:center; color:#ff4a4a;'>Ошибка загрузки лидеров</div>";
        console.error(e);
    }
}

function updateShopUI() {
    clickLevelDesc.innerText = `Уровень: ${clickLevel} (+${clickPower} за клик)`;
    buyClickBtn.innerText = `${upgradeCost} 💰`;
}

// Клик по молнии
clickBtn.addEventListener('click', async () => {
    score += clickPower;
    scoreEl.innerText = score;
    
    clickBtn.style.transform = 'scale(0.95)';
    setTimeout(() => clickBtn.style.transform = 'scale(1)', 50);

    try {
        await fetch(`${BACKEND_URL}/click`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, username: username, clicks: clickPower })
        });
    } catch (e) { console.error(e); }
});

// Логика покупки апгрейда
buyClickBtn.addEventListener('click', async () => {
    if (score >= upgradeCost) {
        score -= upgradeCost;
        scoreEl.innerText = score;

        clickLevel += 1;
        clickPower += 1;
        
        const costPaid = upgradeCost;
        upgradeCost = Math.round(upgradeCost * 2.5);

        updateShopUI();

        try {
            await fetch(`${BACKEND_URL}/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    user_id: userId, 
                    username: username, 
                    clicks: -costPaid,
                    click_level: clickLevel,
                    click_power: clickPower
                })
            });
        } catch (e) { console.error(e); }
        tg.HapticFeedback.notificationOccurred("success");
    } else {
        alert("Недостаточно монет! 😢");
        tg.HapticFeedback.notificationOccurred("error");
    }
});

loadUserData();