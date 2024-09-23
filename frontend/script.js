let session_id = null;

document.getElementById('chat-icon').addEventListener('click', function () {
    document.getElementById('chat-bubble').style.display = 'flex';
    document.getElementById('chat-icon').style.display = 'none';
    initiateChat();
});

document.getElementById('close-chat').addEventListener('click', function () {
    document.getElementById('chat-bubble').style.display = 'none';
    document.getElementById('chat-icon').style.display = 'block';
});

function initiateChat() {
    addBotMessage('Bonjour 👋');
    addBotMessage('Nous avons déjà discuté ensemble 🙂 ?');
    logInteraction('chat_initiated', {});
    addChoices([
        { text: 'Oui', handler: handleInitialYes },
        { text: 'Non', handler: handleInitialNo }
    ]);
}

function addUserMessage(message) {
    let chatMessages = document.getElementById('chat-messages');
    let userMessageElement = document.createElement('div');
    userMessageElement.className = 'user-message';
    userMessageElement.textContent = message;
    chatMessages.appendChild(userMessageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
    logInteraction('user_message', { message: message });
}

function addBotMessage(message) {
    let chatMessages = document.getElementById('chat-messages');
    let botMessageElement = document.createElement('div');
    botMessageElement.className = 'bot-message';
    botMessageElement.innerHTML = message;
    chatMessages.appendChild(botMessageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight; // Scroll to bottom
    logInteraction('bot_message', { message: message });
}

function addChoices(choices) {
    let buttonContainer = document.getElementById('button-container');
    buttonContainer.innerHTML = ''; // Clear previous buttons

    choices.forEach(choice => {
        let button = document.createElement('button');
        button.className = 'option';
        button.textContent = choice.text;
        button.addEventListener('click', function () {
            addUserMessage(choice.text);
            buttonContainer.innerHTML = ''; // Clear choices
            choice.handler();
        });
        buttonContainer.appendChild(button);
    });
}

function handleInitialYes() {
    addBotMessage('Re-bonjour 😊');
    addBotMessage('Tu es là pour ...');
    addChoices([
        { text: 'Poser une question', handler: handleAskQuestion }
    ]);
}

function handleInitialNo() {
    addBotMessage('Bonjour 😊 !');
    addBotMessage('Tu es là pour ...');
    addChoices([
        { text: 'Poser une question', handler: handleAskQuestion }
    ]);
}

function handleAskQuestion() {
    addBotMessage('D\'accord ! 👍');
    addBotMessage('Si je ne suis pas en mesure de te donner une réponse immédiate, je vais contacter l\'entreprise CAP Recouvrement afin de trouver une réponse à ta question.');
    addBotMessage('Donc avant de poser ta question, j’aurais besoin de quelques informations pour que l\'entreprise te réponde au mieux.');
    addChoices([
        { text: 'OK', handler: handleRequestInfo }
    ]);
}

function handleRequestInfo() {
    addBotMessage('Puis-je connaître ton nom ?');
    let input = document.createElement('input');
    input.setAttribute('type', 'text');
    input.setAttribute('id', 'user-name');
    input.setAttribute('placeholder', 'Tapez votre nom');
    document.getElementById('button-container').appendChild(input);
    input.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            handleUserName();
        }
    });
}

function handleUserName() {
    let nameInput = document.getElementById('user-name');
    let userName = nameInput.value.trim();
    if (userName) {
        addUserMessage(userName);
        nameInput.remove();
        addBotMessage('Et ton prénom ?');
        let input = document.createElement('input');
        input.setAttribute('type', 'text');
        input.setAttribute('id', 'user-firstname');
        input.setAttribute('placeholder', 'Tapez votre prénom');
        document.getElementById('button-container').appendChild(input);
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                handleUserFirstname();
            }
        });
    }
}

function handleUserFirstname() {
    let firstnameInput = document.getElementById('user-firstname');
    let userFirstname = firstnameInput.value.trim();
    if (userFirstname) {
        addUserMessage(userFirstname);
        firstnameInput.remove();
        addBotMessage('Entrez votre code client');
        let input = document.createElement('input');
        input.setAttribute('type', 'text');
        input.setAttribute('id', 'user-code-client');
        input.setAttribute('placeholder', 'Tapez votre code client');
        document.getElementById('button-container').appendChild(input);
        input.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                handleUserCodeClient();
            }
        });
    }
}

function handleUserCodeClient() {
    let codeClientInput = document.getElementById('user-code-client');
    let userCodeClient = codeClientInput.value.trim();
    if (userCodeClient) {
        addUserMessage(userCodeClient);
        codeClientInput.remove();
        
        // Vérifier si le débiteur est présent dans le fichier Excel avec nom, prénom, et code client
        fetch('http://127.0.0.1:8000/api/verify_user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                first_name: document.getElementById('user-firstname').value.trim(), 
                last_name: document.getElementById('user-name').value.trim(),
                code_client: userCodeClient
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.found) {
                session_id = data.session_id;
                addBotMessage('Merci ! Que voulez-vous savoir ?');
                addChoices([
                    { text: 'A qui dois-je de l\'argent ?', handler: () => askQuestion('A qui dois-je de l\'argent ?') },
                    { text: 'Qui est le créancier ?', handler: () => askQuestion('Qui est le créancier ?') },
                    { text: 'Qui est mon gestionnaire de dossier ?', handler: () => askQuestion('Qui est mon gestionnaire de dossier ?') },
                    { text: 'Puis-je payer en plusieurs fois ?', handler: () => askQuestion('Puis-je payer en plusieurs fois ?') },
                    { text: 'Puis-je reculer l\'échéance de ce mois ?', handler: () => askQuestion('Puis-je reculer l\'échéance de ce mois ?') },
                    { text: 'Pourquoi je paye les frais ?', handler: () => askQuestion('Pourquoi je paye les frais ?') },
                    { text: 'J\'ai résilié !', handler: () => askQuestion('J\'ai résilié !') },
                    { text: 'Autre question ?', handler: handleOtherQuestion }
                ]);
            } else {
                addBotMessage('Désolé, nous n\'avons pas trouvé vos informations dans notre base de données.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addBotMessage('Une erreur s\'est produite. Veuillez réessayer plus tard.');
        });
    }
}

function askQuestion(question) {
    addUserMessage(question);
    fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            message: question, 
            first_name: document.getElementById('user-firstname').value.trim(), 
            last_name: document.getElementById('user-name').value.trim(),
            code_client: document.getElementById('user-code-client').value.trim(),
            session_id: session_id 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.session_id) {
            session_id = data.session_id;
        }
        addBotMessage(data.response);
        addBotMessage('Vous avez besoin d\'autre chose ?');
        addChoices([
            { text: 'Oui', handler: () => handleAskAnotherQuestion(question) },
            { text: 'Non', handler: () => addBotMessage('D\'accord, au revoir! 👋') }
        ]);
    })
    .catch(error => {
        console.error('Error:', error);
        addBotMessage('Une erreur s\'est produite. Veuillez réessayer plus tard.');
    });
}

function handleOtherQuestion() {
    addBotMessage('Veuillez écrire votre question :');
    let input = document.createElement('input');
    input.setAttribute('type', 'text');
    input.setAttribute('id', 'user-other-question');
    input.setAttribute('placeholder', 'Tapez votre question');
    document.getElementById('button-container').appendChild(input);
    input.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            handleUserOtherQuestion();
        }
    });
}

function handleUserOtherQuestion() {
    let questionInput = document.getElementById('user-other-question');
    let userQuestion = questionInput.value.trim();
    if (userQuestion) {
        addUserMessage(userQuestion);
        questionInput.remove();
        askQuestion(userQuestion);
    }
}

function handleAskAnotherQuestion(previousQuestion) {
    const questions = [
        'A qui dois-je de l\'argent ?',
        'Qui est le créancier ?',
        'Qui est mon gestionnaire de dossier ?',
        'Puis-je payer en plusieurs fois ?',
        'Puis-je reculer l\'échéance de ce mois ?',
        'Pourquoi je paye les frais ?',
        'J\'ai résilié !',
        'Autre question ?'
    ].filter(q => q !== previousQuestion);

    addChoices(questions.map(q => ({ text: q, handler: () => {
        if (q === 'Autre question ?') {
            handleOtherQuestion();
        } else {
            askQuestion(q);
        }
    }})));
}
