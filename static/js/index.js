function give_rating(value, comment_id) {
  // Инициализировать новый запрос
  const request = new XMLHttpRequest();
  request.open('POST', '/rating_comment');

  // Функция обратного вызова, когда запрос завершен
  request.onload = () => {

      // Извлечение данных JSON из запроса
      const data = JSON.parse(request.responseText);

      // Обновите result div
      if (data.success) {
          document.querySelectorAll('.record-star-item').forEach(star => {
              star.style.opacity = '0';
          });
          let list_stars = document.querySelectorAll('.record-star-item');
          let i = 0;
          for (let elem of list_stars) {
              if (i < value) {
                  elem.style.opacity = '100';
                  i++;
              }
          }
          document.querySelector('.record-block-info > p').innerHTML = data.new_value_comment
      }
  }
  // Добавить данные для отправки с запросом
  const data = new FormData();
  data.append('value_rating', value);
  data.append('comment_id', comment_id);

  // Послать запрос
  request.send(data);
  return false;
};


function make_complaint(comment_id) {
  // Инициализировать новый запрос
  const request = new XMLHttpRequest();
  request.open('POST', '/record/complaint/' + comment_id);

  // Функция обратного вызова, когда запрос завершен
  request.onload = () => {

      // Извлечение данных JSON из запроса
      const data = JSON.parse(request.responseText);

      // Обновите result div
      if (data.success) {
          document.querySelector('.message-complaint').innerHTML = 'Жалоба успешно отправлена'
      }
  }
  // Добавить данные для отправки с запросом
  const data = new FormData();
  data.append('comment_id', comment_id);

  // Послать запрос
  request.send(data);
  return false;
};