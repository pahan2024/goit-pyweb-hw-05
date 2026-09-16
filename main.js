console.log('Hello world!')

// Знаходимо елементи з HTML сторінки
const formChat = document.getElementById('formChat')
const textField = document.getElementById('textField')
const subscribe = document.getElementById('subscribe')

// Виконуємо з'єднання до веб-сокету
const ws = new WebSocket('ws://localhost:8080')

// Обробляємо подію submit форми
formChat.addEventListener('submit', (e) => {
    e.preventDefault() // Зупиняємо стандартну обробку форми браузером
    if (!textField.value.trim()) return // Не відправляємо порожні рядки
    
    ws.send(textField.value) // Надсилаємо текст на сервер
    textField.value = null // Обнуляємо поле введення
})

// Подія відкриття з'єднання
ws.onopen = (e) => {
    console.log('Hello WebSocket!')
}

// Обробка повідомлень від сервера
ws.onmessage = (e) => {
    console.log(e.data)
    const text = e.data

    const elMsg = document.createElement('div')
    
    // ВАЖЛИВО: цей рядок змушує браузер відображати переноси рядків (\n) від сервера
    elMsg.style.whiteSpace = 'pre-wrap' 
    elMsg.style.marginBottom = '8px'
    
    elMsg.textContent = text
    subscribe.appendChild(elMsg)
    
    // Автоматичний скролл до низу
    subscribe.scrollTop = subscribe.scrollHeight
}
