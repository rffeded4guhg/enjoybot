// scripts.js
document.addEventListener('DOMContentLoaded', () => {
    const clientId = 'YOUR_CLIENT_ID';
    const serverInvite = 'YOUR_SERVER_INVITE';

    document.getElementById('invite-bot').addEventListener('click', () => {
        window.open(`https://discord.com/oauth2/authorize?client_id=${clientId}&permissions=8&scope=bot`, '_blank');
    });

    document.getElementById('join-server').addEventListener('click', () => {
        window.open(`https://discord.gg/${serverInvite}`, '_blank');
    });
});
