## 1. Архитектура приложения

Ключевые компоненты:

1. Веб-сервис (Backend)  
   - Принимает запросы от пользователей (через REST API или аналогичный протокол).  
   - Обрабатывает входные данные (изображения, координаты взглядов, параметры агрегации).  
   - Обращается к сервисам ядра системы (модуль генерации тепловой карты, база данных/хранилище и т.д.).  
   - Возвращает результат (готовые тепловые карты или ссылки на них) либо JSON-ответ с нужной информацией.

2. Модуль агрегации и построения тепловых карт  
   - Содержит логику формирования тепловых карт: ядерная оценка плотности (KDE), выбор методов, параметров (bandwidth, шаг сетки, метод вычисления).  
   - Реализует разные уровни детализации (например, разные разрешения сетки).  
   - Может работать как отдельный сервис или быть частью бэкенда.

3. Хранилище данных  
   - Содержит:
     - Метаданные об изображениях (страницы, ID прототипов, версии макетов).  
     - Сырые данные взглядов (координаты, время, пользователь, дополнительные атрибуты – возраст, пол, устройство и т.д.).  
     - Сгенерированные тепловые карты (можно хранить в кэше или в постоянном хранилище для повторного использования).  
   - В простейшем случае можно хранить в файловой системе (изображения и JSON с координатами), но при росте объёмов и повышенных требованиях лучше использовать БД (например, PostgreSQL, MongoDB и т.п.).  
   - Важно продумать схему хранения и индексы для эффективных выборок по срезам (пол, возраст, ID страницы).

4. Система кэширования  
   - Позволяет сохранять уже рассчитанные тепловые карты, чтобы при повторном запросе с теми же параметрами не пересчитывать всё заново.  
   - Может быть реализована в оперативной памяти (in-memory кэш), в Redis, либо в виде файлового кэша (с ключом вида «ID страницы + метод + bandwidth + разрешение»).

5. Фронтенд  
   - Веб-интерфейс, где пользователь выбирает параметры агрегации (тип ядра, уровень детализации, фильтрацию по полу/возрасту, временным периодам и т.д.).  
   - Отправляет запросы к бэкенду и отображает результаты (тепловые карты) поверх исходного изображения.  
   - При масштабировании можно вынести фронтенд на отдельный сервер/хостинг, но взаимодействие идёт через HTTP(S).

6. Масштабирование  
   - Горизонтальное масштабирование (несколько экземпляров бэкенда) + балансировщик нагрузки.  
   - При необходимости можно выделить отдельный сервис генерации тепловых карт, который обрабатывает тяжёлые вычислительные задачи.  
   - Хранилище (БД) настраивается под шардирование/репликацию при больших объёмах данных.

7. Мониторинг и логирование  
   - Сбор метрик (время генерации тепловых карт, нагрузка, ошибки, время отклика).  
   - Логи запросов (кто, что запросил, какие параметры).  
   - Интеграция с системами мониторинга (Prometheus, Grafana) – в продакшене.

8. Безопасность и доступ  
   - Авторизация и аутентификация пользователей (JWT-токены или другой механизм).  
   - Ограничение доступа к чувствительным данным (например, отдельные срезы доступны только админам или исследователям).  
   - HTTPS для шифрования передачи данных.  
   - Политика прав доступа к разным методам (CRUD-операции, выгрузка результатов и т.д.).


## 2. Хранение данных

1. Метаданные и срезы  
   - В БД (или файлах) храним список страниц/прототипов, к которым привязаны координаты взглядов.  
   - Для каждого «сеанса» (участника исследования) храним: ID пользователя, пол, возраст, время сессии, набор координат (x,y), время фиксации и т.д.

2. Изображения  
   - Храним отдельно в файловой системе или в объектном хранилище (S3-совместимом). В БД кладём только путь/URL.

3. Сгенерированные тепловые карты  
   - Для кэша: можно хранить в оперативной памяти (словарь Python), в Redis или на диске (файл .png).  
   - Ключ кэша: комбинация (ID страницы, метод KDE, bandwidth, разрешение сетки, срез данных по полу, возрасту и т.п.).  
   - Если пользователь повторно запрашивает ту же комбинацию, отдаём готовый результат.


## 3. Система кэширования

- In-memory кэш (например, словарь dict), если данных немного и нужен быстрый доступ.  
- При перезапуске приложения такой кэш обнуляется, поэтому для более стойкого хранения можно сохранять готовые тепловые карты на диск (в каталог cache/) с именами файлов, формируемыми по ключу кэша.  
- Для больших нагрузок и распределённой системы – использовать Redis (но в задании сказано «без библиотек», так что на практике это уже вопрос реального проекта).



## 4. Взаимодействие с фронтендом

- REST API: фронтенд отправляет HTTP-запросы на эндпоинты бэкенда, передавая параметры фильтрации (пол, возраст), параметры ядра (bandwidth), метод вычисления, уровень детализации и т.д.  
- Бэкенд отвечает либо URL-адресом готового изображения (тепловой карты), либо отдаёт его напрямую (с типом image/png).  
- Можно также отдавать JSON, в котором будет информация о статусе генерации, особенно если вычисление тяжёлое и мы делаем асинхронную очередь задач.


## 5. Масштабирование

1. Горизонтальное масштабирование  
   - Запуск нескольких экземпляров бэкенда (Docker-контейнеры), перед ними – балансировщик нагрузки (NGINX, HAProxy, AWS ELB).  
   - Кэш можно сделать распределённым (Redis) или согласованным между экземплярами.

2. Отдельный сервис генерации  
   - Если генерация тепловых карт очень ресурсоёмкая, можно вынести её в отдельный микросервис, куда бэкенд отправляет задачу.  
   - Микросервис возвращает результат или сохраняет его в кэш/базу.

3. Хранилище  
   - При больших объёмах данных – кластерная СУБД, либо NoSQL (MongoDB, Cassandra).  
   - Для файлов (изображений) – объектное хранилище (MinIO, S3).




## 6. Мониторинг и логирование

1. Логирование  
   - Логируем запросы пользователей, ошибки, время генерации тепловых карт.  
   - Храним логи в отдельных файлах, либо отправляем в систему централизованного логирования (ELK stack, например).

2. Мониторинг  
   - Метрики: число запросов в секунду, среднее время ответа, нагрузка на ЦПУ, использование памяти.  
   - При необходимости – алерты при превышении порогов.



## 7. Безопасность и доступ

1. Авторизация  
   - JWT-токены или session-based аутентификация.  
   - Уровни доступа: исследователи, администраторы, внешние пользователи.  
2. Шифрование  
   - Использование HTTPS для всех запросов.  
3. Очистка/обезличивание данных  
   - Если речь о персональных данных (возраст, пол, привязка к конкретным пользователям), важно анонимизировать их или хранить с соблюдением законодательства (GDPR и т.д.).





