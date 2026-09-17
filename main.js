console.log('Hello world!')

// ОБЯЗАТЕЛЬНО: Находим элементы на странице, иначе браузер выдаст ошибку
const formChat = document.getElementById('formChat')
const textField = document.getElementById('textField')
const subscribe = document.getElementById('subscribe')

const ws = new WebSocket('ws://localhost:8080')

formChat.addEventListener('submit', (e) => {
    e.preventDefault()
    if (!textField.value.trim()) return // Защита от пустых строк
    ws.send(textField.value)
    textField.value = null
})

ws.onopen = (e) => {
    console.log('Hello WebSocket!')
}

ws.onmessage = (e) => {
    console.log(e.data)
    const text = e.data

    const elMsg = document.createElement('div')
    // Сохраняем переносы строк (\n) от сервера
    elMsg.style.whiteSpace = 'pre-wrap' 
    elMsg.style.marginBottom = '8px'
    
    elMsg.textContent = text
    subscribe.appendChild(elMsg)
    
    // Автоматический скролл вниз
    subscribe.scrollTop = subscribe.scrollHeight
}
