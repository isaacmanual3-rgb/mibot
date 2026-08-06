# ─────────────────────────────────────────────────────────────
#  TRANSLATIONS  —  CraftGems / MiBot
#  Supported languages: en (English) | es (Spanish) | ar (Arabic, RTL)
# ─────────────────────────────────────────────────────────────

TRANSLATIONS = {

    # ── NAVIGATION ─────────────────────────────────────────────
    'nav_home':      {'en': 'HOME',       'es': 'INICIO', 'ar': 'الرئيسية'},
    'nav_mining':    {'en': 'MINING',     'es': 'MINERÍA', 'ar': 'التعدين'},
    'nav_tasks':     {'en': 'TASKS',      'es': 'TAREAS', 'ar': 'المهام'},
    'nav_invite':    {'en': 'INVITE',     'es': 'INVITAR', 'ar': 'دعوة'},
    'nav_wallet':    {'en': 'WALLET',     'es': 'BILLETERA', 'ar': 'المحفظة'},
    'nav_explore':   {'en': 'EXPLORE',    'es': 'EXPLORAR', 'ar': 'استكشاف'},
    'nav_promo':     {'en': 'PROMO CODE', 'es': 'CÓDIGO PROMO', 'ar': 'رمز ترويجي'},
    'nav_support':   {'en': 'SUPPORT',    'es': 'SOPORTE', 'ar': 'الدعم'},
    'nav_referrals': {'en': 'REFERRALS',  'es': 'REFERIDOS', 'ar': 'الإحالات'},

    # ── BOTTOM NAV ─────────────────────────────────────────────
    'bnav_home':   {'en': 'HOME',   'es': 'INICIO', 'ar': 'الرئيسية'},
    'bnav_mine':   {'en': 'MINE',   'es': 'MINAR', 'ar': 'تعدين'},
    'bnav_rush':   {'en': 'RUSH',   'es': 'RUSH', 'ar': 'راش'},
    'bnav_invite': {'en': 'INVITE', 'es': 'INVITAR', 'ar': 'دعوة'},
    'bnav_tasks':  {'en': 'TASKS',  'es': 'TAREAS', 'ar': 'المهام'},
    'bnav_top':    {'en': 'TOP',    'es': 'TOP', 'ar': 'المتصدرون'},
    'bnav_wallet': {'en': 'WALLET', 'es': 'CARTERA', 'ar': 'المحفظة'},
    'bnav_profile':{'en': 'PROFILE','es': 'PERFIL', 'ar': 'الملف'},

    # ── Profile page ──
    'pf_wallet_title':     {'en': 'Withdrawal Wallet',    'es': 'Wallet de Retiro', 'ar': 'محفظة السحب'},
    'pf_language':         {'en': 'Language',              'es': 'Idioma', 'ar': 'اللغة'},
    # ── Canal obligatorio (join_channel.html) ──
    'jc_title':            {'en': 'JOIN OUR CHANNEL',      'es': 'ÚNETE AL CANAL', 'ar': 'انضم إلى قناتنا'},
    'jc_subtitle':         {'en': 'You must join our channel to use the app', 'es': 'Debes unirte a nuestro canal para usar la app', 'ar': 'يجب الانضمام إلى قناتنا لاستخدام التطبيق'},
    'jc_not_yet':          {'en': 'You have not joined yet. Please join the channel first.', 'es': 'Aún no te has unido. Únete al canal primero.', 'ar': 'لم تنضم بعد. يرجى الانضمام إلى القناة أولاً.'},
    'jc_join_btn':         {'en': '📢 JOIN CHANNEL',        'es': '📢 UNIRME AL CANAL', 'ar': '📢 انضم إلى القناة'},
    'jc_check_btn':        {'en': "✓ I'VE JOINED",          'es': '✓ YA ME UNÍ', 'ar': '✓ لقد انضممت'},
    'jc_footer':           {'en': 'Join the channel, then tap "I have joined"', 'es': 'Únete al canal y luego toca "Ya me uní"', 'ar': 'انضم إلى القناة ثم اضغط «لقد انضممت»'},
    'pf_wallet_linked':    {'en': 'Wallet linked',         'es': 'Wallet vinculada', 'ar': 'تم ربط المحفظة'},
    'pf_wallet_not_linked':{'en': 'No wallet linked',      'es': 'Sin wallet vinculada', 'ar': 'لا توجد محفظة مرتبطة'},
    'pf_wallet_none':      {'en': 'Add your TON address to withdraw', 'es': 'Añade tu dirección TON para retirar', 'ar': 'أضف عنوان TON الخاص بك للسحب'},
    'pf_wallet_link':      {'en': 'LINK WALLET',           'es': 'VINCULAR WALLET', 'ar': 'ربط المحفظة'},
    'pf_wallet_edit':      {'en': 'EDIT WALLET',           'es': 'EDITAR WALLET', 'ar': 'تعديل المحفظة'},
    'pf_wallet_save':      {'en': 'SAVE',                  'es': 'GUARDAR', 'ar': 'حفظ'},
    'pf_wallet_cancel':    {'en': 'CANCEL',                'es': 'CANCELAR', 'ar': 'إلغاء'},
    'pf_wallet_hint':      {'en': 'Enter a valid TON wallet (UQ... or EQ...). This is where your withdrawals will be sent.', 'es': 'Ingresa una wallet TON válida (UQ... o EQ...). Aquí se enviarán tus retiros.', 'ar': 'أدخل محفظة TON صحيحة (‎UQ...‎ أو ‎EQ...‎). ستُرسل عمليات السحب إلى هذا العنوان.'},
    'pf_wallet_locked':    {'en': 'Wallet verified & protected · contact support to change it', 'es': 'Wallet verificada y protegida · contacta soporte para cambiarla', 'ar': 'المحفظة موثّقة ومحمية · تواصل مع الدعم لتغييرها'},
    'pf_wallet_lock_warn': {'en': '⚠ You can only link your wallet ONCE. Make sure it is correct.', 'es': '⚠ Solo puedes vincular tu wallet UNA vez. Verifica que sea correcta.', 'ar': '⚠ يمكنك ربط المحفظة مرة واحدة فقط. تأكد من صحتها.'},
    'pf_wallet_empty':     {'en': 'Enter a wallet address', 'es': 'Ingresa una dirección de wallet', 'ar': 'أدخل عنوان المحفظة'},
    'pf_wallet_error':     {'en': 'Could not save wallet',  'es': 'No se pudo guardar la wallet', 'ar': 'تعذّر حفظ المحفظة'},

    'pf_plan_title':       {'en': 'Plan Status',           'es': 'Estado del Plan', 'ar': 'حالة الخطة'},
    'pf_plan_none':        {'en': 'No active plan',         'es': 'Sin plan activo', 'ar': 'لا توجد خطة نشطة'},
    'pf_plan_activate_hint':{'en': 'Activate a plan to start mining', 'es': 'Activa un plan para empezar a minar', 'ar': 'فعّل خطة لبدء التعدين'},
    'pf_plan_active':      {'en': 'ACTIVE',                'es': 'ACTIVO', 'ar': 'نشطة'},
    'pf_plan_inactive':    {'en': 'INACTIVE',              'es': 'INACTIVO', 'ar': 'غير نشطة'},
    'pf_plan_expires':     {'en': 'Expires',               'es': 'Vence', 'ar': 'تنتهي'},
    'pf_plan_go':          {'en': '→ GO TO MINING STATION', 'es': '→ IR A LA ESTACIÓN DE MINERÍA', 'ar': '→ الذهاب إلى محطة التعدين'},

    'pf_stats_title':      {'en': 'Statistics',            'es': 'Estadísticas', 'ar': 'الإحصائيات'},
    'pf_stat_earned':      {'en': 'Total Earned',          'es': 'Total Ganado', 'ar': 'إجمالي الأرباح'},
    'pf_stat_refs':        {'en': 'Referrals',             'es': 'Referidos', 'ar': 'الإحالات'},
    'pf_stat_machines':    {'en': 'Machines',              'es': 'Máquinas', 'ar': 'الأجهزة'},
    'pf_stat_ref_earn':    {'en': 'Ref. Earnings',         'es': 'Ganancia Ref.', 'ar': 'أرباح الإحالات'},

    'pf_account_title':    {'en': 'Account Info',          'es': 'Información de Cuenta', 'ar': 'معلومات الحساب'},
    'pf_row_id':           {'en': 'User ID',               'es': 'ID de Usuario', 'ar': 'معرّف المستخدم'},
    'pf_row_user':         {'en': 'Username',              'es': 'Usuario', 'ar': 'اسم المستخدم'},
    'pf_row_member':       {'en': 'Member Since',          'es': 'Miembro Desde', 'ar': 'عضو منذ'},
    'pf_row_balance':      {'en': 'Balance',               'es': 'Saldo', 'ar': 'الرصيد'},
    'pf_copied':           {'en': 'Copied!',               'es': '¡Copiado!', 'ar': 'تم النسخ!'},
    'pf_support_title':    {'en': 'SUPPORT',               'es': 'SOPORTE', 'ar': 'الدعم'},
    'pf_support_sub':      {'en': 'Need help? Contact our support team on Telegram.', 'es': '¿Necesitas ayuda? Contacta a nuestro equipo de soporte en Telegram.', 'ar': 'تحتاج مساعدة؟ تواصل مع فريق الدعم على تيليجرام.'},


    # ── BASE / HEADER ──────────────────────────────────────────
    'balance_label':   {'en': 'TON BALANCE',          'es': 'SALDO TON', 'ar': 'رصيد TON'},
    'loading_text':    {'en': 'LOADING QUEST DATA...', 'es': 'CARGANDO DATOS...', 'ar': 'جارٍ تحميل بيانات المهمة...'},
    'lang_btn_switch': {'en': '🌐 ES',                'es': '🌐 EN', 'ar': '🌐 AR'},

    # ── INDEX ──────────────────────────────────────────────────
    'idx_player_online': {'en': '▶ PLAYER ONLINE',         'es': '▶ JUGADOR EN LÍNEA', 'ar': '▶ اللاعب متصل'},
    'idx_daily_quest':   {'en': 'START MINING TODAY', 'es': 'EMPIEZA A MINAR HOY', 'ar': 'ابدأ التعدين اليوم'},
    'idx_daily_sub':     {'en': 'Activate a plan and earn TON automatically 24/7', 'es': 'Activa un plan y gana TON automaticamente 24/7', 'ar': 'فعّل خطة واربح TON تلقائيًا على مدار الساعة'},
    'idx_ticker':        {
        'en': '★ TON QUEST DAILY REWARDS ★    EARN TON EVERY DAY ★    COMPLETE QUESTS FOR BONUS TON ★    INVITE FRIENDS & MULTIPLY YOUR EARNINGS ★    MUCH WOW. VERY EARN. SO TON. ★',
        'es': '★ RECOMPENSAS DIARIAS TON ★    GANA TON CADA DÍA ★    COMPLETA MISIONES PARA BONUS ★    INVITA AMIGOS Y MULTIPLICA TUS GANANCIAS ★    MUCHO WOW. MUY GANAR. ASÍ TON. ★', 'ar': '★ مكافآت TON اليومية ★    اربح TON كل يوم ★    أكمل المهام لمكافآت إضافية ★    ادعُ أصدقاءك وضاعف أرباحك ★'},
    'idx_stats_label':   {'en': '📊  YOUR STATS',       'es': '📊  TUS ESTADÍSTICAS', 'ar': '📊  إحصائياتك'},
    'idx_stat_balance':  {'en': 'BALANCE',               'es': 'SALDO', 'ar': 'الرصيد'},
    'idx_stat_earned':   {'en': 'TOTAL EARNED',          'es': 'TOTAL GANADO', 'ar': 'إجمالي الأرباح'},
    'idx_stat_machines': {'en': 'MACHINES',              'es': 'MÁQUINAS', 'ar': 'الأجهزة'},
    'idx_stat_refs':     {'en': 'REFERRALS',             'es': 'REFERIDOS', 'ar': 'الإحالات'},
    'idx_actions_label': {'en': 'QUICK ACTIONS',      'es': 'ACCIONES RÁPIDAS', 'ar': 'إجراءات سريعة'},
    'idx_btn_mining':    {'en': 'MINE',                'es': 'MINERIA', 'ar': 'تعدين'},
    'idx_btn_tasks':     {'en': 'TASKS',               'es': 'TAREAS', 'ar': 'المهام'},
    'idx_btn_invite':    {'en': 'INVITE',              'es': 'INVITAR', 'ar': 'دعوة'},
    'idx_btn_wallet':    {'en': 'WALLET',              'es': 'BILLETERA', 'ar': 'المحفظة'},
    'idx_quest_label':   {'en': 'QUEST LOG',           'es': 'DIARIO DE MISIONES', 'ar': 'سجل المهام'},
    'idx_quest_1':       {'en': 'BUY A MINING PLAN to start auto-earning TON', 'es': 'ACTIVA UN PLAN DE MINERIA para ganar TON automaticamente', 'ar': 'اشترِ خطة تعدين لبدء ربح TON تلقائيًا'},
    'idx_quest_2':       {'en': 'COMPLETE TASKS for bonus earnings',            'es': 'COMPLETA TAREAS para obtener ganancias extra', 'ar': 'أكمل المهام للحصول على أرباح إضافية'},
    'idx_quest_3':       {'en': 'INVITE FRIENDS to earn referral bonuses',      'es': 'INVITA AMIGOS para ganar bonos por referidos', 'ar': 'ادعُ أصدقاءك لكسب مكافآت الإحالة'},
    'idx_quest_4':       {'en': 'WITHDRAW your TON to your wallet',             'es': 'RETIRA tu TON a tu billetera', 'ar': 'اسحب TON إلى محفظتك'},

    # ── INDEX MINING DASHBOARD ─────────────────────────────────
    'mdb_total_pending':   {'en': '⛏ TOTAL PENDING',     'es': '⛏ TOTAL PENDIENTE', 'ar': '⛏ إجمالي المعلّق'},
    'mdb_per_hour':        {'en': 'PER HOUR',             'es': 'POR HORA', 'ar': 'في الساعة'},
    'mdb_per_day':         {'en': 'PER DAY',              'es': 'POR DÍA', 'ar': 'في اليوم'},
    'mdb_mining_progress': {'en': '⚡ MINING PROGRESS',  'es': '⚡ PROGRESO DE MINERÍA', 'ar': '⚡ تقدّم التعدين'},
    'mdb_hashrate_monitor':{'en': 'HASHRATE MONITOR',     'es': 'MONITOR DE HASHRATE', 'ar': 'مراقب قوة التعدين'},
    'mdb_machines_lbl':    {'en': 'MACHINES',             'es': 'MÁQUINAS', 'ar': 'الأجهزة'},
    'mdb_plan_lbl':        {'en': 'PLAN',                 'es': 'PLAN', 'ar': 'الخطة'},
    'mdb_expires_lbl':     {'en': 'EXPIRES',              'es': 'VENCE', 'ar': 'تنتهي'},
    'mdb_uptime_lbl':      {'en': 'UPTIME',               'es': 'ACTIVO', 'ar': 'مدة التشغيل'},
    'mdb_mining_console':  {'en': 'MINING CONSOLE',       'es': 'CONSOLA DE MINERÍA', 'ar': 'وحدة التعدين'},
    'mdb_loading_rewards': {'en': '⏳ LOADING REWARDS...','es': '⏳ CARGANDO RECOMPENSAS...', 'ar': '⏳ جارٍ تحميل المكافآت...'},
    'mdb_mining_rewards':  {'en': '⛏ MINING... REWARDS ACCUMULATING', 'es': '⛏ MINANDO... RECOMPENSAS ACUMULANDO', 'ar': '⛏ جارٍ التعدين... تتراكم المكافآت'},
    'mdb_claim_btn':       {'en': '💰 CLAIM',             'es': '💰 RECLAMAR', 'ar': '💰 استلام'},
    'mdb_manage_plans':    {'en': '⛏ MANAGE MINING PLANS →', 'es': '⛏ GESTIONAR PLANES →', 'ar': '⛏ إدارة خطط التعدين →'},
    'mdb_rig_offline':     {'en': 'RIG OFFLINE',          'es': 'RIG INACTIVO', 'ar': 'الجهاز متوقف'},
    'mdb_buy_plan_to_start':{'en': 'PURCHASE A PLAN TO START\nEARNING TON AUTOMATICALLY', 'es': 'COMPRA UN PLAN PARA EMPEZAR\nA GANAR TON AUTOMÁTICAMENTE', 'ar': 'اشترِ خطة لبدء\\nربح TON تلقائيًا'},
    'mdb_get_started':     {'en': '⛏ GET STARTED NOW',   'es': '⛏ EMPEZAR AHORA', 'ar': '⛏ ابدأ الآن'},
    'mdb_online':          {'en': 'ONLINE',               'es': 'EN LÍNEA', 'ar': 'متصل'},
    'mdb_offline':         {'en': 'OFFLINE',              'es': 'INACTIVO', 'ar': 'غير متصل'},
    'mdb_starter_tier':    {'en': 'STARTER TIER',         'es': 'NIVEL INICIAL', 'ar': 'المستوى المبتدئ'},
    'mdb_intermediate':    {'en': 'INTERMEDIATE',         'es': 'INTERMEDIO', 'ar': 'متوسط'},
    'mdb_advanced':        {'en': 'ADVANCED',             'es': 'AVANZADO', 'ar': 'متقدم'},
    'mdb_max_power':       {'en': 'MAXIMUM POWER',        'es': 'POTENCIA MÁXIMA', 'ar': 'أقصى قوة'},
    'mdb_earn_ton_hr':     {'en': 'EARN TON/HR',          'es': 'GANA TON/HR', 'ar': 'اربح TON/ساعة'},
    'mdb_2x':              {'en': '2× FASTER',            'es': '2× MÁS RÁPIDO', 'ar': 'أسرع ٢×'},
    'mdb_5x':              {'en': '5× FASTER',            'es': '5× MÁS RÁPIDO', 'ar': 'أسرع ٥×'},
    'mdb_max_ton':         {'en': '🔥 MAX TON',           'es': '🔥 MÁX TON', 'ar': '🔥 أقصى TON'},
    'mdb_processing':      {'en': '⏳ PROCESSING...',     'es': '⏳ PROCESANDO...', 'ar': '⏳ جارٍ المعالجة...'},
    'mdb_claim_rewards':   {'en': '💰 CLAIM REWARDS',     'es': '💰 RECLAMAR RECOMPENSAS', 'ar': '💰 استلام المكافآت'},
    'mdb_connection_error':{'en': 'Connection error',     'es': 'Error de conexión', 'ar': 'خطأ في الاتصال'},
    'mdb_claim_failed':    {'en': 'Claim failed',         'es': 'Error al reclamar', 'ar': 'فشل الاستلام'},

    # ── MINING PAGE ────────────────────────────────────────────
    'mn_ticker': {
        'en': '★ MINING STATION ★    PURCHASE MACHINES & EARN AUTOMATICALLY ★    CLAIM PENDING REWARDS ANYTIME ★    MORE MACHINES = MORE TON PER HOUR ★    MUCH MINE. VERY PASSIVE. SO TON. ★',
        'es': '★ ESTACIÓN DE MINERÍA ★    COMPRA MÁQUINAS Y GANA AUTOMÁTICAMENTE ★    RECLAMA RECOMPENSAS CUANDO QUIERAS ★    MÁS MÁQUINAS = MÁS TON POR HORA ★    MUCHO MINAR. MUY PASIVO. ASÍ TON. ★', 'ar': '★ محطة التعدين ★    اشترِ الأجهزة واربح تلقائيًا ★    استلم المكافآت في أي وقت ★    أجهزة أكثر = TON أكثر في الساعة ★'},
    'mn_title':          {'en': 'MINING STATION',           'es': 'ESTACIÓN DE MINERÍA', 'ar': 'محطة التعدين'},
    'mn_sub':            {'en': 'Purchase mining machines and earn TON automatically!', 'es': '¡Compra máquinas mineras y gana TON automáticamente!', 'ar': 'اشترِ أجهزة التعدين واربح TON تلقائيًا!'},
    'mn_stat_machines':  {'en': 'Machines',                 'es': 'Máquinas', 'ar': 'الأجهزة'},
    'mn_stat_ton_hour':  {'en': 'TON/Hour',                 'es': 'TON/Hora', 'ar': 'TON/ساعة'},
    'mn_stat_pending':   {'en': 'Pending',                  'es': 'Pendiente', 'ar': 'معلّق'},
    'mn_claim_btn':      {'en': 'CLAIM',                    'es': 'RECLAMAR', 'ar': 'استلام'},
    'mn_your_machines':  {'en': 'Your Machines',            'es': 'Tus Máquinas', 'ar': 'أجهزتك'},
    'mn_mining_status':  {'en': 'MINING',                   'es': 'MINANDO', 'ar': 'يعدّن'},
    'mn_expires':        {'en': 'Exp:',                     'es': 'Vence:', 'ar': 'ينتهي:'},
    'mn_machines_label': {'en': 'Mining Machines',          'es': 'Máquinas Mineras', 'ar': 'أجهزة التعدين'},
    'mn_purchase_desc':  {'en': 'Purchase a miner to start earning TON automatically!', 'es': '¡Compra un minero para empezar a ganar TON automáticamente!', 'ar': 'اشترِ جهاز تعدين لبدء ربح TON تلقائيًا!'},
    'mn_free_badge':     {'en': '★ FREE',                   'es': '★ GRATIS', 'ar': '★ مجاني'},
    'mn_30_days':        {'en': '30 DAYS',                  'es': '30 DÍAS', 'ar': '٣٠ يومًا'},
    'mn_30d_return':     {'en': '30-day return',            'es': 'Retorno en 30 días', 'ar': 'عائد ٣٠ يومًا'},
    'mn_n_days':         {'en': '{days} DAYS',              'es': '{days} DÍAS', 'ar': '{days} يومًا'},
    'mn_1_day':          {'en': '1 DAY',                   'es': '1 DÍA', 'ar': 'يوم واحد'},
    'mn_nd_return':      {'en': '{days}-day return',        'es': 'Retorno en {days} días', 'ar': 'عائد {days} يومًا'},
    'mn_1d_return':      {'en': '1-day return',             'es': 'Retorno en 1 día', 'ar': 'عائد يوم واحد'},
    'mn_ton_hr':         {'en': 'TON/hr',                   'es': 'TON/hr', 'ar': 'TON/ساعة'},
    'mn_ton_day':        {'en': 'TON/day',                  'es': 'TON/día', 'ar': 'TON/يوم'},
    'mn_ton_month':      {'en': 'TON/mo',                   'es': 'TON/mes', 'ar': 'TON/شهر'},
    'mn_activate_free':  {'en': '★ ACTIVATE FREE',          'es': '★ ACTIVAR GRATIS', 'ar': '★ تفعيل مجاني'},
    'mn_activate_paid':  {'en': '⚡ ACTIVATE FOR',          'es': '⚡ ACTIVAR POR', 'ar': '⚡ فعّل مقابل'},
    'mn_renewable':      {'en': '↻ Renewable on expiry',    'es': '↻ Renovable al vencer', 'ar': '↻ قابلة للتجديد عند الانتهاء'},
    'mn_how_title':      {'en': 'How It Works',             'es': 'Cómo Funciona', 'ar': 'كيف يعمل'},
    'mn_step1':          {'en': 'Purchase a miner',         'es': 'Compra un minero', 'ar': 'اشترِ جهاز تعدين'},
    'mn_step2':          {'en': 'Mining starts auto',       'es': 'Minería automática', 'ar': 'يبدأ التعدين تلقائيًا'},
    'mn_step3':          {'en': 'Claim rewards',            'es': 'Reclama recompensas', 'ar': 'استلم المكافآت'},
    'mn_step4':          {'en': 'Withdraw TON!',            'es': '¡Retira TON!', 'ar': 'اسحب TON!'},
    'mn_no_plans':       {'en': 'NO PLANS AVAILABLE',       'es': 'SIN PLANES DISPONIBLES', 'ar': 'لا توجد خطط متاحة'},
    'mn_check_back':     {'en': 'Check back soon!',         'es': '¡Vuelve pronto!', 'ar': 'عد قريبًا!'},
    'mn_modal_title':    {'en': 'CONFIRM PLAN',             'es': 'CONFIRMAR PLAN', 'ar': 'تأكيد الخطة'},
    'mn_modal_activate': {'en': 'Activate this plan?',       'es': '¿Activar este plan?', 'ar': 'تفعيل هذه الخطة؟'},
    'mn_modal_cost':     {'en': 'Cost',                     'es': 'Costo', 'ar': 'التكلفة'},
    'mn_modal_balance':  {'en': 'Your Balance',             'es': 'Tu Saldo', 'ar': 'رصيدك'},
    'mn_modal_free':     {'en': '✨ FREE',                  'es': '✨ GRATIS', 'ar': '✨ مجاني'},
    'mn_modal_cancel':   {'en': 'CANCEL',                   'es': 'CANCELAR', 'ar': 'إلغاء'},
    'mn_modal_confirm':  {'en': 'CONFIRM',                  'es': 'CONFIRMAR', 'ar': 'تأكيد'},

    # ── Adsgram free-plan task gate ──
    'mn_ads_title':      {'en': 'UNLOCK FREE PLAN',         'es': 'DESBLOQUEA PLAN GRATIS', 'ar': 'افتح الخطة المجانية'},
    'mn_ads_sub_1':      {'en': 'Watch {n} rewarded videos to activate the',  'es': 'Mira {n} videos con recompensa para activar el plan', 'ar': 'شاهد {n} إعلانات مكافأة لتفعيل'},
    'mn_ads_sub_2':      {'en': 'plan.',                    'es': '.', 'ar': 'الخطة.'},
    'mn_ads_progress':   {'en': 'Ads watched',              'es': 'Anuncios vistos', 'ar': 'الإعلانات المشاهَدة'},
    'mn_ads_watch':      {'en': 'WATCH AD',                 'es': 'VER ANUNCIO', 'ar': 'شاهد إعلانًا'},
    'mn_ads_wait':       {'en': 'WAIT {s}s',               'es': 'ESPERA {s}s', 'ar': 'انتظر {s} ثانية'},
    'mn_ads_loading':    {'en': 'LOADING AD...',            'es': 'CARGANDO...', 'ar': 'جارٍ تحميل الإعلان...'},
    'mn_ads_activate':   {'en': 'ACTIVATE PLAN',            'es': 'ACTIVAR PLAN', 'ar': 'تفعيل الخطة'},
    'mn_ads_hint':       {'en': 'Watch all ads to unlock activation',      'es': 'Mira todos los anuncios para desbloquear', 'ar': 'شاهد جميع الإعلانات لفتح التفعيل'},
    'mn_ads_complete':   {'en': '✓ ALL ADS COMPLETED',      'es': '✓ ANUNCIOS COMPLETADOS', 'ar': '✓ اكتملت جميع الإعلانات'},
    'mn_ads_counted':    {'en': '✓ Ad counted · {n} left',  'es': '✓ Anuncio contado · faltan {n}', 'ar': '✓ تم احتساب الإعلان · بقي {n}'},
    'mn_ads_incomplete': {'en': 'Ad not completed. Try again.',             'es': 'Anuncio no completado. Inténtalo de nuevo.', 'ar': 'لم يكتمل الإعلان. حاول مرة أخرى.'},
    'mn_ads_closed_early': {'en': '⚠ You closed the ad too soon. Not counted.', 'es': '⚠ Cerraste el anuncio muy pronto. No contó.', 'ar': '⚠ أغلقت الإعلان مبكرًا. لم يُحتسب.'},
    'mn_ads_click_title': {'en': 'You must click the ad!',                   'es': '¡Debes hacer click en el anuncio!', 'ar': 'يجب النقر على الإعلان!'},
    'mn_ads_click_desc': {'en': 'You watched the ad but didn\'t interact with it. To get credit you must click and open the advertised app.', 'es': 'Viste el anuncio pero no interactuaste con él. Para que cuente debes hacer click y abrir la app anunciada.', 'ar': 'شاهدت الإعلان لكنك لم تنقر عليه.'},
    'mn_ads_click_step1': {'en': 'Watch the full ad',                        'es': 'Mira el anuncio completo', 'ar': 'شاهد الإعلان كاملًا'},
    'mn_ads_click_step2': {'en': 'Tap / click on the ad',                    'es': 'Toca / haz click en el anuncio', 'ar': 'انقر على الإعلان'},
    'mn_ads_click_step3': {'en': 'Open the advertised app briefly',          'es': 'Abre la app anunciada un momento', 'ar': 'افتح التطبيق المُعلن عنه للحظات'},
    'mn_ads_click_understood': {'en': 'GOT IT',                              'es': 'ENTENDIDO', 'ar': 'فهمت'},

    # ── Captcha de verificación (verify.html) ──
    'vf_title':          {'en': 'VERIFICATION',                    'es': 'VERIFICACIÓN', 'ar': 'التحقق'},
    'vf_subtitle':       {'en': "Please confirm you're human to continue", 'es': 'Confirma que eres humano para continuar', 'ar': 'يرجى تأكيد أنك إنسان للمتابعة'},
    'vf_error':          {'en': '⚠ Verification failed. Please try again.', 'es': '⚠ Verificación fallida. Inténtalo de nuevo.', 'ar': '⚠ فشل التحقق. حاول مرة أخرى.'},
    'vf_continue':       {'en': 'CONTINUE',                        'es': 'CONTINUAR', 'ar': 'متابعة'},
    'vf_protected':      {'en': 'Protected by reCAPTCHA',          'es': 'Protegido por reCAPTCHA', 'ar': 'محمي بواسطة reCAPTCHA'},
    'mn_ads_unavailable':{'en': 'No ad available. Try again shortly.',      'es': 'No hay anuncio disponible. Intenta en un momento.', 'ar': 'لا يوجد إعلان متاح. حاول بعد قليل.'},

    'mn_processing':     {'en': 'PROCESSING...',            'es': 'PROCESANDO...', 'ar': 'جارٍ المعالجة...'},
    'mn_claiming':       {'en': 'CLAIMING...',              'es': 'RECLAMANDO...', 'ar': 'جارٍ الاستلام...'},
    'mn_purchase_failed':{'en': 'Purchase failed',          'es': 'Compra fallida', 'ar': 'فشل الشراء'},
    'mn_claim_failed':   {'en': 'Claim failed',             'es': 'Error al reclamar', 'ar': 'فشل الاستلام'},
    'mn_conn_error':     {'en': 'Connection error',         'es': 'Error de conexión', 'ar': 'خطأ في الاتصال'},
    'mn_free_label':     {'en': 'FREE',                     'es': 'GRATIS', 'ar': 'مجاني'},
    # Wallet deposit section
    'wl_dep_memo_warning': {
        'en': '⚠ Include the MEMO/Comment mandatorily',
        'es': '⚠ Incluye el MEMO/Comentario obligatoriamente', 'ar': '⚠ أدرج المذكرة (MEMO) إلزاميًا'},
    'wl_dep_address_lbl':  {'en': 'TON ADDRESS (send here)',    'es': 'DIRECCIÓN TON (envía aquí)', 'ar': 'عنوان TON (أرسل هنا)'},
    'wl_dep_memo_lbl':     {'en': 'MEMO / COMMENT (required ⚠)', 'es': 'MEMO / COMENTARIO (obligatorio ⚠)', 'ar': 'المذكرة / التعليق (مطلوب ⚠)'},
    'wl_dep_memo_warn2': {
        'en': '⚠ If you do not include the MEMO your deposit will not be credited automatically.',
        'es': '⚠ Si no incluyes el MEMO tu depósito no se acreditará automáticamente.', 'ar': '⚠ إذا لم تُدرج المذكرة فلن يُضاف إيداعك تلقائيًا.'},
    'wl_dep_waiting':      {'en': 'WAITING FOR DEPOSIT...',     'es': 'ESPERANDO DEPÓSITO...', 'ar': 'في انتظار الإيداع...'},
    'wl_dep_auto_credit':  {'en': 'Will be credited automatically in seconds', 'es': 'Se acreditará automáticamente en segundos', 'ar': 'ستتم الإضافة تلقائيًا خلال ثوانٍ'},
    'wl_dep_credited':     {'en': 'TON CREDITED!',              'es': '¡TON ACREDITADO!', 'ar': 'تمت إضافة TON!'},
    # Mining JS dynamic strings (via window.I18N)
    'mn_activate_plan_msg': {
        'en': 'Activate the {name} plan?',
        'es': '¿Activar el plan {name}?', 'ar': 'تفعيل خطة {name}؟'},

    # ── WALLET PAGE ────────────────────────────────────────────
    'wl_ticker': {
        'en': '★ YOUR TON WALLET ★    SEND & RECEIVE TON ★    MINIMUM WITHDRAWAL REQUIRED ★    EARNINGS ACCUMULATE AUTOMATICALLY ★',
        'es': '★ TU BILLETERA TON ★    ENVÍA Y RECIBE TON ★    SE REQUIERE RETIRO MÍNIMO ★    LAS GANANCIAS SE ACUMULAN AUTOMÁTICAMENTE ★', 'ar': '★ محفظة TON الخاصة بك ★    أرسل واستقبل TON ★    يوجد حد أدنى للسحب ★    الأرباح تتراكم تلقائيًا ★'},
    'wl_title':          {'en': 'YOUR WALLET',              'es': 'TU BILLETERA', 'ar': 'محفظتك'},
    'wl_ton_balance':    {'en': 'TON BALANCE',              'es': 'SALDO TON', 'ar': 'رصيد TON'},
    'wl_total_earned':   {'en': 'Total Earned',             'es': 'Total Ganado', 'ar': 'إجمالي الأرباح'},
    'wl_from_referrals': {'en': 'From Referrals',           'es': 'Por Referidos', 'ar': 'من الإحالات'},
    'wl_withdraw_btn':   {'en': 'WITHDRAW',                 'es': 'RETIRAR', 'ar': 'سحب'},
    'wl_withdraw_desc':  {'en': 'Send TON out',             'es': 'Enviar TON', 'ar': 'إرسال TON'},
    'wl_deposit_btn':    {'en': 'DEPOSIT',                  'es': 'DEPOSITAR', 'ar': 'إيداع'},
    'wl_deposit_desc':   {'en': 'Receive TON',              'es': 'Recibir TON', 'ar': 'استقبال TON'},
    'wl_no_transactions':{'en': 'NO TRANSACTIONS YET',      'es': 'AÚN SIN TRANSACCIONES', 'ar': 'لا توجد معاملات بعد'},
    'wl_complete_tasks': {'en': 'Complete tasks to start earning TON!', 'es': '¡Completa tareas para empezar a ganar TON!', 'ar': 'أكمل المهام لتبدأ ربح TON!'},
    'wl_transactions':   {'en': 'TRANSACTION HISTORY',      'es': 'HISTORIAL DE TRANSACCIONES', 'ar': 'سجل المعاملات'},
    'wl_withdraw_title': {'en': 'WITHDRAW TON',             'es': 'RETIRAR TON', 'ar': 'سحب TON'},
    'wl_amount':         {'en': 'Amount (TON)',              'es': 'Cantidad (TON)', 'ar': 'المبلغ (TON)'},
    'wl_address':        {'en': 'TON Wallet Address',        'es': 'Dirección de Billetera TON', 'ar': 'عنوان محفظة TON'},
    'wl_address_hint':   {'en': 'Must start with "EQ" or "UQ"', 'es': 'Debe empezar con "EQ" o "UQ"', 'ar': 'يجب أن يبدأ بـ «EQ» أو «UQ»'},
    'wl_network_fee':    {'en': 'Network Fee',               'es': 'Comisión de Red', 'ar': 'رسوم الشبكة'},
    'wl_you_receive':    {'en': 'You Receive',               'es': 'Recibirás', 'ar': 'ستستلم'},
    'wl_cancel':         {'en': 'CANCEL',                    'es': 'CANCELAR', 'ar': 'إلغاء'},
    'wl_submit_withdraw':{'en': 'WITHDRAW',                  'es': 'RETIRAR', 'ar': 'سحب'},
    'wl_deposit_title':  {'en': 'DEPOSIT TON',               'es': 'DEPOSITAR TON', 'ar': 'إيداع TON'},
    'wl_deposit_addr_lbl':{'en': 'Deposit Address',          'es': 'Dirección de Depósito', 'ar': 'عنوان الإيداع'},
    'wl_wallet_from_profile': {'en': 'Wallet loaded from your profile', 'es': 'Wallet cargada desde tu perfil', 'ar': 'تم تحميل المحفظة من ملفك الشخصي'},
    'wl_link_in_profile':    {'en': '⚠ Link your wallet from your Profile first', 'es': '⚠ Primero vincula tu wallet desde tu Perfil', 'ar': '⚠ اربط محفظتك من الملف الشخصي أولاً'},
    'wl_deposit_from_any':{'en': 'Send TON from any wallet or exchange.', 'es': 'Envía TON desde cualquier billetera o exchange.', 'ar': 'أرسل TON من أي محفظة أو منصة تداول.'},
    'wl_insufficient':   {'en': 'Insufficient balance',      'es': 'Saldo insuficiente', 'ar': 'الرصيد غير كافٍ'},
    'wl_invalid_addr':   {'en': 'Invalid TON address',       'es': 'Dirección TON inválida', 'ar': 'عنوان TON غير صالح'},
    'wl_processing':     {'en': 'PROCESSING...',             'es': 'PROCESANDO...', 'ar': 'جارٍ المعالجة...'},
    'wl_copy':           {'en': 'COPY',                      'es': 'COPIAR', 'ar': 'نسخ'},
    'wl_copied':         {'en': 'COPIED!',                   'es': '¡COPIADO!', 'ar': 'تم النسخ!'},
    'wl_available':      {'en': 'Available',                 'es': 'Disponible', 'ar': 'متاح'},
    'wl_processing_wd':  {'en': 'PROCESSING WITHDRAWAL...', 'es': 'PROCESANDO RETIRO...', 'ar': 'جارٍ معالجة السحب...'},
    'wl_withdrawal_sent':{'en': 'WITHDRAWAL SENT!',         'es': '¡RETIRO ENVIADO!', 'ar': 'تم إرسال السحب!'},
    'wl_retry':          {'en': 'TRY AGAIN',                'es': 'INTENTAR DE NUEVO', 'ar': 'حاول مرة أخرى'},
    'wl_enter_address':  {'en': 'Enter your TON address',   'es': 'Ingresa tu dirección TON', 'ar': 'أدخل عنوان TON الخاص بك'},
    'wl_min_amount':     {'en': 'Minimum',                  'es': 'Mínimo', 'ar': 'الحد الأدنى'},
    'wl_invalid_addr_hint': {
        'en': '⚠ Invalid TON address. Must start with UQ or EQ and be 48 characters. Copy it directly from your wallet or exchange.',
        'es': '⚠ Dirección TON inválida. Debe empezar con UQ o EQ y tener 48 caracteres. Cópiala directamente de tu wallet o exchange.', 'ar': '⚠ عنوان TON غير صالح. يجب أن يبدأ بـ UQ أو EQ وأن يتكون من ٤٨ حرفًا. انسخه مباشرة من محفظتك أو منصة التداول.'},
    'wl_amount_placeholder': {'en': 'Enter amount',         'es': 'Ingresa cantidad', 'ar': 'أدخل المبلغ'},
    'wl_ton_addr_placeholder': {
        'en': 'UQ... or EQ... (any wallet or exchange)',
        'es': 'UQ... o EQ... (cualquier wallet o exchange)', 'ar': '‎UQ...‎ أو ‎EQ...‎ (أي محفظة أو منصة)'},
    # JS notification strings (used via window.I18N in main.js)
    'js_connection_error':    {'en': 'Connection error',                    'es': 'Error de conexión', 'ar': 'خطأ في الاتصال'},
    'js_link_copied':         {'en': 'Link copied!',                        'es': '¡Enlace copiado!', 'ar': 'تم نسخ الرابط!'},
    'js_enter_valid_amount':  {'en': 'Enter a valid amount',                'es': 'Ingresa una cantidad válida', 'ar': 'أدخل مبلغًا صحيحًا'},
    'js_enter_valid_wallet':  {'en': 'Enter a valid TON wallet address',    'es': 'Ingresa una dirección TON válida', 'ar': 'أدخل عنوان محفظة TON صحيحًا'},
    'js_withdrawal_submitted':{'en': 'Withdrawal request submitted!',       'es': '¡Solicitud de retiro enviada!', 'ar': 'تم إرسال طلب السحب!'},
    'js_withdrawal_failed':   {'en': 'Withdrawal failed',                   'es': 'Error al procesar el retiro', 'ar': 'فشل السحب'},
    'js_enter_promo':         {'en': 'Enter a promo code',                  'es': 'Ingresa un código promo', 'ar': 'أدخل رمزًا ترويجيًا'},
    'js_invalid_code':        {'en': 'Invalid code',                        'es': 'Código inválido', 'ar': 'رمز غير صالح'},
    'js_verifying':           {'en': 'Verifying completion...',             'es': 'Verificando...', 'ar': 'جارٍ التحقق من الإكمال...'},
    'js_task_failed':         {'en': 'Could not complete task',             'es': 'No se pudo completar la tarea', 'ar': 'تعذّر إكمال المهمة'},
    'js_already_claimed':     {'en': 'Already claimed today!',              'es': '¡Ya reclamaste hoy!', 'ar': 'تم الاستلام اليوم بالفعل!'},

    # ── TASKS PAGE ─────────────────────────────────────────────
    'tq_ticker': {
        'en': '★ DAILY QUESTS ★    COMPLETE TASKS TO EARN TON ★    NEW TASKS ADDED REGULARLY ★    BONUS REWARDS FOR STREAKS ★',
        'es': '★ MISIONES DIARIAS ★    COMPLETA TAREAS Y GANA TON ★    NUEVAS TAREAS REGULARMENTE ★    RECOMPENSAS EXTRA POR RACHAS ★', 'ar': '★ المهام اليومية ★    أكمل المهام لتربح TON ★    تُضاف مهام جديدة باستمرار ★    مكافآت إضافية للمواظبة ★'},
    'tq_title':       {'en': 'QUEST BOARD',               'es': 'TABLERO DE MISIONES', 'ar': 'لوحة المهام'},
    'tq_sub':         {'en': 'Complete quests to earn TON rewards!', 'es': '¡Completa misiones para ganar recompensas TON!', 'ar': 'أكمل المهام لتربح مكافآت TON!'},
    'tq_completed':   {'en': 'Completed',                 'es': 'Completadas', 'ar': 'مكتملة'},
    'tq_earned':      {'en': 'Earned',                    'es': 'Ganado', 'ar': 'المكتسب'},
    'tq_available':   {'en': 'Available',                 'es': 'Disponibles', 'ar': 'متاحة'},
    'tq_cat_all':     {'en': '◈ All',                     'es': '◈ Todas', 'ar': '◈ الكل'},
    'tq_cat_social':  {'en': '◉ Social',                  'es': '◉ Social', 'ar': '◉ اجتماعية'},
    'tq_cat_daily':   {'en': '◎ Daily',                   'es': '◎ Diario', 'ar': '◎ يومية'},
    'tq_cat_special': {'en': '★ Special',                 'es': '★ Especial', 'ar': '★ خاصة'},
    'tq_claimed_badge':{'en': 'CLAIMED',                  'es': 'RECLAMADO', 'ar': 'تم الاستلام'},
    'tq_locked_badge':{'en': 'LOCKED',                    'es': 'BLOQUEADO', 'ar': 'مقفلة'},
    'tq_no_tasks':    {'en': 'NO TASKS AVAILABLE',        'es': 'SIN TAREAS DISPONIBLES', 'ar': 'لا توجد مهام متاحة'},
    'tq_check_soon':  {'en': 'Check back soon for new quests!', 'es': '¡Vuelve pronto para nuevas misiones!', 'ar': 'عد قريبًا لمهام جديدة!'},
    'tq_verify_membership':{'en': 'VERIFY MEMBERSHIP',   'es': 'VERIFICAR MEMBRESÍA', 'ar': 'تحقق من العضوية'},
    'tq_join_channel':{'en': 'Join channel',              'es': 'Únete al canal', 'ar': 'انضم إلى القناة'},
    'tq_click_verify':{'en': 'Click verify',              'es': 'Haz clic en verificar', 'ar': 'اضغط تحقّق'},
    'tq_get_reward':  {'en': 'Get reward!',               'es': '¡Obtén recompensa!', 'ar': 'احصل على المكافأة!'},
    'tq_cancel':      {'en': 'CANCEL',                    'es': 'CANCELAR', 'ar': 'إلغاء'},
    'tq_verify':      {'en': 'VERIFY',                    'es': 'VERIFICAR', 'ar': 'تحقّق'},
    'tq_checking':    {'en': 'CHECKING...',               'es': 'VERIFICANDO...', 'ar': 'جارٍ التحقق...'},
    # ── Check-in diario (sistema propio) ──
    'tq_checkin_title':  {'en': 'Daily Check-In',          'es': 'Check-In Diario', 'ar': 'تسجيل الدخول اليومي'},
    'tq_checkin_desc':   {'en': 'Claim your daily reward', 'es': 'Reclama tu recompensa diaria', 'ar': 'استلم مكافأتك اليومية'},
    'tq_checkin_streak': {'en': 'day streak',              'es': 'días seguidos', 'ar': 'يوم متتالٍ'},
    'tq_claim':          {'en': 'CLAIM',                   'es': 'RECLAMAR', 'ar': 'استلام'},
    'tq_claimed':        {'en': 'CLAIMED',                 'es': 'RECLAMADO', 'ar': 'تم الاستلام'},
    'tq_open':           {'en': 'OPEN',                    'es': 'ABRIR', 'ar': 'فتح'},
    'tq_checkin_day':    {'en': 'Day',                     'es': 'Día', 'ar': 'اليوم'},
    'tq_checkin_modal_desc': {'en': 'Claim every day for 30 days. Rewards grow each day!', 'es': '¡Reclama cada día durante 30 días. La recompensa sube cada día!', 'ar': 'سجّل دخولك يوميًا لمدة ٣٠ يومًا. المكافآت تزداد كل يوم!'},
    'tq_checkin_watch_claim': {'en': 'WATCH AD & CLAIM',   'es': 'VER ANUNCIO Y RECLAMAR', 'ar': 'شاهد الإعلان واستلم'},
    'tq_checkin_ad_note': {'en': 'You must watch the ad and tap it to claim', 'es': 'Debes ver el anuncio y hacer click en él para reclamar', 'ar': 'يجب مشاهدة الإعلان والنقر عليه للاستلام'},
    'tq_checkin_wait':   {'en': 'Come back later',         'es': 'Vuelve más tarde', 'ar': 'عد لاحقًا'},
    # ── Pantalla de IP en uso (límite de cuentas por IP) ──
    'ipu_title':         {'en': 'IP ALREADY IN USE',       'es': 'IP EN USO', 'ar': 'عنوان IP مستخدم بالفعل'},
    'ipu_subtitle':      {'en': 'This internet connection is already being used by another account. Only one account per network is allowed.',
                          'es': 'Esta conexión a internet ya está siendo usada por otra cuenta. Solo se permite una cuenta por red.', 'ar': 'هذا الاتصال بالإنترنت مستخدم من حساب آخر. يُسمح بحساب واحد فقط لكل شبكة.'},
    'ipu_step1':         {'en': 'Switch networks: use mobile data instead of wifi (or the other way around)',
                          'es': 'Cambia de red: usa tus datos móviles en vez del wifi (o al revés)', 'ar': 'غيّر الشبكة: استخدم بيانات الهاتف بدل الواي فاي (أو العكس)'},
    'ipu_step2':         {'en': 'Or turn on a VPN to get a different IP',
                          'es': 'O activa una VPN para obtener una IP diferente', 'ar': 'أو شغّل VPN للحصول على عنوان IP مختلف'},
    'ipu_step3':         {'en': 'Open the app again',      'es': 'Vuelve a abrir la app', 'ar': 'افتح التطبيق مرة أخرى'},
    'ipu_retry':         {'en': 'TRY AGAIN',               'es': 'REINTENTAR', 'ar': 'حاول مرة أخرى'},
    'ipu_support':       {'en': 'If you think this is a mistake, contact us:',
                          'es': 'Si crees que es un error, escríbenos:', 'ar': 'إذا كنت تظن أن هذا خطأ، تواصل معنا:'},
    'tq_tasks_label': {'en': '★  ACTIVE QUESTS',          'es': '★  MISIONES ACTIVAS', 'ar': '★  المهام النشطة'},
    'tq_start_btn':   {'en': 'START ▶',                   'es': 'INICIAR ▶', 'ar': 'ابدأ ▶'},
    'tq_verify_hint': {
        'en': 'Join the channel and click verify to claim your reward!',
        'es': '¡Únete al canal y haz clic en verificar para reclamar tu recompensa!', 'ar': 'انضم إلى القناة واضغط تحقّق لاستلام مكافأتك!'},
    'tq_quest_done':  {'en': 'Quest completed! +{reward} TON', 'es': '¡Misión completada! +{reward} TON', 'ar': 'اكتملت المهمة! ‎+{reward}‎ TON'},
    'tq_verify_fail': {'en': 'Verification failed',       'es': 'Verificación fallida', 'ar': 'فشل التحقق'},
    'tq_task_fail':   {'en': 'Task failed',               'es': 'Error en la tarea', 'ar': 'فشلت المهمة'},

    # ── INVITE PURCHASE TASK ───────────────────────────────────
    'tq_invite_task_title': {
        'en': '👥 Invite & Earn 10%',
        'es': '👥 Invita y Gana 10%', 'ar': '👥 ادعُ واربح ١٠٪'},
    'tq_invite_task_desc': {
        'en': 'Friend buys a plan → you earn 10% in TON',
        'es': 'Tu amigo compra un plan → ganas 10% en TON', 'ar': 'صديقك يشتري خطة ← تربح ١٠٪ بعملة TON'},
    'tq_invite_btn':   {'en': 'INVITE',   'es': 'INVITAR', 'ar': 'دعوة'},
    'tq_invite_rewarded_one':   {'en': '✓ 1 friend rewarded',    'es': '✓ 1 amigo recompensado', 'ar': '✓ تمت مكافأة صديق واحد'},
    'tq_invite_rewarded_many':  {'en': '✓ {n} friends rewarded', 'es': '✓ {n} amigos recompensados', 'ar': '✓ تمت مكافأة {n} أصدقاء'},
    # Wallet withdrawal success messages
    'wl_wd_auto_sent':{'en': '✅ TON sent automatically!', 'es': '✅ ¡TON enviado automáticamente!', 'ar': '✅ تم إرسال TON تلقائيًا!'},
    'wl_wd_in_process':{'en': '⏳ Withdrawal registered and being processed', 'es': '⏳ Retiro registrado y en proceso', 'ar': '⏳ تم تسجيل السحب وجارٍ معالجته'},
    'wl_wd_to':       {'en': 'To:',                       'es': 'A:', 'ar': 'إلى:'},
    'wl_wd_id':       {'en': 'ID:',                       'es': 'ID:', 'ar': 'المعرّف:'},
    'wl_wd_send_soon':{'en': 'TON will be sent in the next few minutes.', 'es': 'El TON se enviará en los próximos minutos.', 'ar': 'سيتم إرسال TON خلال الدقائق القادمة.'},
    'wl_view_wallet': {'en': '🔍 View my wallet on Tonviewer',
                       'es': '🔍 Ver mi wallet en Tonviewer', 'ar': '🔍 عرض محفظتي على Tonviewer'},
    'api_wallet_linked_once': {
        'en': 'Wallet linked successfully. For security, you can only link it once.',
        'es': 'Wallet vinculada correctamente. Por seguridad, solo puedes vincularla una vez.', 'ar': 'تم ربط المحفظة بنجاح. لأسباب أمنية، يمكنك ربطها مرة واحدة فقط.'},
    # Wallet deposit success messages
    'wl_dep_received':{'en': 'TON received',              'es': 'TON recibidos', 'ar': 'تم استلام TON'},
    'wl_dep_credited_to':{'en': 'TON credited to your account', 'es': 'TON acreditados a tu cuenta', 'ar': 'تمت إضافة TON إلى حسابك'},

    # ── REFERRALS PAGE ─────────────────────────────────────────
    'rf_ticker': {
        'en': '★ REFER & EARN ★    INVITE FRIENDS FOR INSTANT REWARDS ★    EARN EVERY TIME A FRIEND JOINS ★    UNLIMITED REFERRALS ★',
        'es': '★ REFIERE Y GANA ★    INVITA AMIGOS Y GANA RECOMPENSAS INSTANTÁNEAS ★    GANA CADA VEZ QUE UN AMIGO SE UNE ★    REFERIDOS ILIMITADOS ★', 'ar': '★ ادعُ واربح ★    ادعُ أصدقاءك لمكافآت فورية ★    اربح مع كل صديق ينضم ★    إحالات غير محدودة ★'},
    'rf_title':          {'en': 'INVITE FRIENDS',          'es': 'INVITAR AMIGOS', 'ar': 'ادعُ أصدقاءك'},
    'rf_sub':            {'en': 'Earn TON when your friend activates a plan — even the free one!', 'es': '¡Gana TON cuando tu amigo activa un plan — incluso el gratuito!', 'ar': 'اربح TON عندما يفعّل صديقك خطة — حتى المجانية!'},
    'rf_total_invites':  {'en': 'Total Invites',           'es': 'Total Invitados', 'ar': 'إجمالي الدعوات'},
    'rf_validated':      {'en': 'Validated',               'es': 'Validados', 'ar': 'مؤكدة'},
    'rf_pending':        {'en': 'Pending',                 'es': 'Pendiente', 'ar': 'معلّقة'},
    'rf_total_earned':   {'en': 'Total Earned',            'es': 'Total Ganado', 'ar': 'إجمالي الأرباح'},
    'rf_your_link':      {'en': '🔗 YOUR INVITE LINK',     'es': '🔗 TU ENLACE DE INVITACIÓN', 'ar': '🔗 رابط الدعوة الخاص بك'},
    'rf_copy_link':      {'en': 'COPY LINK',               'es': 'COPIAR ENLACE', 'ar': 'نسخ الرابط'},
    'rf_copied':         {'en': 'COPIED!',                 'es': '¡COPIADO!', 'ar': 'تم النسخ!'},
    'rf_share_link':     {'en': 'Share your link',         'es': 'Comparte tu enlace', 'ar': 'شارك رابطك'},
    'rf_friend_visits':  {'en': 'Friend joins',            'es': 'Tu amigo se une', 'ar': 'ينضم صديقك'},
    'rf_friend_buys':    {'en': 'Activates any plan',      'es': 'Activa cualquier plan', 'ar': 'يفعّل أي خطة'},
    'rf_you_earn':       {'en': 'Earn reward + 5% forever!','es': '¡Recompensa + 5% para siempre!', 'ar': 'اربح مكافأة + ٥٪ للأبد!'},
    'rf_pending_hint':   {'en': 'Pending',   'es': 'Pendiente', 'ar': 'معلّقة'},
    'rf_plan_required':  {
        'en': 'Unlocks when friend activates any plan (free or paid). Then earn 5% of their mining + deposits forever.',
        'es': 'Se activa cuando tu amigo activa cualquier plan (gratuito o de pago). Luego ganas el 5% de su minería + depósitos para siempre.', 'ar': 'تُفتح عندما يفعّل صديقك أي خطة (مجانية أو مدفوعة). بعدها تربح ٥٪ من تعدينه وإيداعاته للأبد.'},
    'rf_commission_badge': {'en': '⚡ 5% LIFETIME',        'es': '⚡ 5% DE POR VIDA', 'ar': '⚡ ٥٪ مدى الحياة'},
    'rf_fraud_badge':      {'en': '✗ FAKE',                'es': '✗ FALSO', 'ar': '✗ مزيّف'},
    'rf_fraud_hint':       {'en': 'No reward — multi-account', 'es': 'Sin recompensa — multicuenta', 'ar': 'لا مكافأة — حسابات متعددة'},
    'rf_how_it_works':   {'en': 'HOW IT WORKS',            'es': 'CÓMO FUNCIONA', 'ar': 'كيف يعمل'},
    'rf_share_telegram': {'en': 'SHARE ON TELEGRAM',       'es': 'COMPARTIR EN TELEGRAM', 'ar': 'شارك على تيليجرام'},
    'rf_share_msg':      {
        'en': '💎 Join Aero flex and earn free TON! Complete missions, mine resources and withdraw real TON.\n\n👇 Enter here:',
        'es': '💎 ¡Únete a Aero flex y gana TON gratis! Completa misiones, mina recursos y retira TON real.\n\n👇 Entra aquí:',
        'pt': '💎 Entre no Aero flex e ganhe TON grátis! Complete missões, mine recursos e retire TON real.\n\n👇 Entre aqui:',
        'fr': '💎 Rejoins Aero flex et gagne du TON gratuit ! Complète des missions, mine des ressources et retire du TON réel.\n\n👇 Entre ici :', 'ar': '💎 انضم إلى Aero flex واربح TON مجانًا! أكمل المهام، عدّن الموارد واسحب TON حقيقيًا.\\n\\n👇 ادخل من هنا:'},
    'rf_friends_list':   {'en': 'YOUR REFERRALS',          'es': 'TUS REFERIDOS', 'ar': 'إحالاتك'},
    'rf_no_friends':     {'en': 'NO REFERRALS YET',        'es': 'AÚN SIN REFERIDOS', 'ar': 'لا توجد إحالات بعد'},
    'rf_invite_first':   {'en': 'Invite your first friend to start earning!', 'es': '¡Invita a tu primer amigo para empezar a ganar!', 'ar': 'ادعُ صديقك الأول لتبدأ الربح!'},

    # ── EXPLORE / LEADERBOARDS ─────────────────────────────────
    'ex_ticker': {
        'en': '★ LEADERBOARDS ★    SEE THE TOP EARNERS ★    CLIMB THE RANKS ★    COMPETE FOR THE TOP SPOT ★',
        'es': '★ CLASIFICACIONES ★    VE LOS MEJORES GANADORES ★    SUBE EN EL RANKING ★    COMPITE POR EL PRIMER LUGAR ★', 'ar': '★ لوحة المتصدرين ★    شاهد أعلى الرابحين ★    ارتقِ في الترتيب ★    نافس على المركز الأول ★'},
    'ex_title':         {'en': 'LEADERBOARDS',             'es': 'CLASIFICACIONES', 'ar': 'لوحة المتصدرين'},
    'ex_sub':           {'en': 'Compete with other questers for the top spots!', 'es': '¡Compite con otros jugadores por los primeros puestos!', 'ar': 'نافس اللاعبين الآخرين على المراكز الأولى!'},
    'ex_your_rank':     {'en': 'YOUR RANK',                'es': 'TU RANGO', 'ar': 'ترتيبك'},
    'ex_current_balance':{'en': 'Current Balance',         'es': 'Saldo Actual', 'ar': 'الرصيد الحالي'},
    'ex_no_data':       {'en': 'NO DATA YET',              'es': 'SIN DATOS AÚN', 'ar': 'لا توجد بيانات بعد'},
    'ex_questers':      {'en': 'Questers',                 'es': 'Jugadores', 'ar': 'اللاعبون'},
    'ex_ton_dist':      {'en': 'TON Dist.',                'es': 'TON Dist.', 'ar': 'TON الموزّع'},
    'ex_checkins':      {'en': 'Check-ins',                'es': 'Check-ins', 'ar': 'تسجيلات الدخول'},
    'ex_tab_rich':      {'en': 'Rich',                     'es': 'Ricos', 'ar': 'الأغنى'},
    'ex_tab_refs':      {'en': 'Popular',                  'es': 'Popular', 'ar': 'الأكثر شعبية'},
    'ex_tab_streak':    {'en': 'Streaks',                  'es': 'Rachas', 'ar': 'المواظبة'},
    'ex_refs_label':    {'en': 'REFS',                     'es': 'REFS', 'ar': 'إحالات'},
    'ex_days_label':    {'en': 'DAYS',                     'es': 'DÍAS', 'ar': 'أيام'},

    # ── PROMO PAGE ─────────────────────────────────────────────
    'pm_ticker': {
        'en': '★ PROMO CODES ★    ENTER A CODE TO EARN BONUS TON ★    LIMITED TIME OFFERS ★    FOLLOW US FOR EXCLUSIVE CODES ★',
        'es': '★ CÓDIGOS PROMO ★    INGRESA UN CÓDIGO PARA GANAR TON EXTRA ★    OFERTAS POR TIEMPO LIMITADO ★    SÍGUENOS PARA CÓDIGOS EXCLUSIVOS ★', 'ar': '★ الرموز الترويجية ★    أدخل رمزًا لتربح TON إضافيًا ★    عروض لوقت محدود ★    تابعنا للحصول على رموز حصرية ★'},
    'pm_title':          {'en': 'PROMO CODES',             'es': 'CÓDIGOS PROMO', 'ar': 'الرموز الترويجية'},
    'pm_sub':            {'en': 'Enter a code to claim bonus TON rewards!', 'es': '¡Ingresa un código para reclamar TON extra!', 'ar': 'أدخل رمزًا للحصول على مكافآت TON إضافية!'},
    'pm_code_hint':      {'en': 'Codes are not case-sensitive', 'es': 'Los códigos no distinguen mayúsculas', 'ar': 'الرموز غير حساسة لحالة الأحرف'},
    'pm_redeem_btn':     {'en': 'REDEEM',                  'es': 'CANJEAR', 'ar': 'استبدال'},
    'pm_no_codes':       {'en': 'NO CODES YET',            'es': 'SIN CÓDIGOS AÚN', 'ar': 'لا توجد رموز بعد'},
    'pm_enter_valid':    {'en': 'Enter a valid code above to claim rewards!', 'es': '¡Ingresa un código válido arriba para reclamar recompensas!', 'ar': 'أدخل رمزًا صحيحًا أعلاه للحصول على المكافآت!'},
    'pm_official_ch':    {'en': 'Official Channel',        'es': 'Canal Oficial', 'ar': 'القناة الرسمية'},
    'pm_official_desc':  {'en': 'Follow our Telegram channel for exclusive drops', 'es': 'Sigue nuestro canal de Telegram para códigos exclusivos', 'ar': 'تابع قناتنا على تيليجرام للحصول على رموز حصرية'},
    'pm_events':         {'en': 'Special Events',          'es': 'Eventos Especiales', 'ar': 'فعاليات خاصة'},
    'pm_events_desc':    {'en': 'Participate in events for limited codes', 'es': 'Participa en eventos para obtener códigos limitados', 'ar': 'شارك في الفعاليات للحصول على رموز محدودة'},
    'pm_partners':       {'en': 'Partnerships',            'es': 'Alianzas', 'ar': 'الشراكات'},
    'pm_partners_desc':  {'en': 'Check our partners for collaboration codes', 'es': 'Consulta nuestros socios para códigos de colaboración', 'ar': 'تحقق من شركائنا للحصول على رموز التعاون'},
    'pm_tip_1':          {'en': 'Each code can only be used once per account', 'es': 'Cada código solo puede usarse una vez por cuenta', 'ar': 'كل رمز يُستخدم مرة واحدة فقط لكل حساب'},
    'pm_tip_2':          {'en': 'Some codes have limited total uses',           'es': 'Algunos códigos tienen usos totales limitados', 'ar': 'بعض الرموز لها عدد استخدامات محدود'},
    'pm_tip_3':          {'en': 'Codes may expire after a certain date',        'es': 'Los códigos pueden expirar después de cierta fecha', 'ar': 'قد تنتهي صلاحية الرموز بعد تاريخ معين'},
    'pm_tip_4':          {'en': 'Keep an eye out for flash codes with big rewards!', 'es': '¡Estate atento a los códigos flash con grandes recompensas!', 'ar': 'ترقّب الرموز السريعة ذات المكافآت الكبيرة!'},
    'pm_redeemed_title': {'en': 'CODE REDEEMED!',          'es': '¡CÓDIGO CANJEADO!', 'ar': 'تم استبدال الرمز!'},
    'pm_you_received':   {'en': 'YOU RECEIVED',            'es': 'RECIBISTE', 'ar': 'لقد استلمت'},
    'pm_awesome':        {'en': 'AWESOME!',                'es': '¡GENIAL!', 'ar': 'رائع!'},
    'pm_checking':       {'en': 'CHECKING...',             'es': 'VERIFICANDO...', 'ar': 'جارٍ التحقق...'},
    'pm_code_history':   {'en': 'REDEEMED CODES',          'es': 'CÓDIGOS CANJEADOS', 'ar': 'الرموز المستبدلة'},
    'pm_where_to_find':  {'en': 'WHERE TO FIND CODES',     'es': 'DÓNDE ENCONTRAR CÓDIGOS', 'ar': 'أين تجد الرموز'},
    'pm_tips_title':     {'en': 'TIPS',                    'es': 'CONSEJOS', 'ar': 'نصائح'},

    # ── BANNED / ERROR / TELEGRAM REQUIRED ─────────────────────
    'banned_title':      {'en': 'Account Banned',          'es': 'Cuenta Baneada', 'ar': 'الحساب محظور'},
    'banned_msg':        {'en': 'Your account has been suspended for violating our terms of service.', 'es': 'Tu cuenta ha sido suspendida por violar nuestros términos de servicio.', 'ar': 'تم تعليق حسابك لمخالفة شروط الخدمة.'},
    'banned_reason':     {'en': 'Reason',                  'es': 'Motivo', 'ar': 'السبب'},
    'banned_contact':    {'en': 'If you believe this is an error, contact support.', 'es': 'Si crees que esto es un error, contacta al soporte.', 'ar': 'إذا كنت تعتقد أن هذا خطأ، تواصل مع الدعم.'},

    'error_title':       {'en': 'Something went wrong',    'es': 'Algo salió mal', 'ar': 'حدث خطأ ما'},
    'error_msg':         {'en': 'An unexpected error occurred. Please try again.', 'es': 'Ocurrió un error inesperado. Por favor intenta de nuevo.', 'ar': 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.'},
    'error_retry':       {'en': 'Try Again',               'es': 'Intentar de nuevo', 'ar': 'حاول مرة أخرى'},

    'tg_required_title': {'en': 'Telegram Required',       'es': 'Telegram Requerido', 'ar': 'تيليجرام مطلوب'},
    'tg_required_msg':   {'en': 'This app must be opened inside Telegram.', 'es': 'Esta app debe abrirse dentro de Telegram.', 'ar': 'يجب فتح هذا التطبيق داخل تيليجرام.'},
    'tg_step1':          {'en': 'Open Telegram',           'es': 'Abre Telegram', 'ar': 'افتح تيليجرام'},
    'tg_step2':          {'en': 'Find our bot',            'es': 'Encuentra nuestro bot', 'ar': 'ابحث عن البوت الخاص بنا'},
    'tg_step3':          {'en': 'Press START',             'es': 'Presiona INICIO', 'ar': 'اضغط START'},

    # ── ADMIN (bilingual for sidebar/header, rest stays EN) ────
    'adm_dashboard':     {'en': 'DASHBOARD',               'es': 'PANEL', 'ar': 'لوحة التحكم'},
    'adm_users':         {'en': 'USERS',                   'es': 'USUARIOS', 'ar': 'المستخدمون'},
    'adm_tasks':         {'en': 'TASKS',                   'es': 'TAREAS', 'ar': 'المهام'},
    'adm_withdrawals':   {'en': 'WITHDRAWALS',             'es': 'RETIROS', 'ar': 'السحوبات'},
    'adm_ton_deposits':  {'en': 'TON DEPOSITS',            'es': 'DEPÓSITOS TON', 'ar': 'إيداعات TON'},
    'adm_promo':         {'en': 'PROMO CODES',             'es': 'CÓDIGOS PROMO', 'ar': 'الرموز الترويجية'},
    'adm_mining':        {'en': 'MINING PLANS',            'es': 'PLANES DE MINERÍA', 'ar': 'خطط التعدين'},
    'adm_config':        {'en': 'CONFIG',                  'es': 'CONFIG', 'ar': 'الإعدادات'},
    'adm_icons':         {'en': 'ICONS',                   'es': 'ÍCONOS', 'ar': 'الأيقونات'},
    'adm_logout':        {'en': 'LOGOUT',                  'es': 'CERRAR SESIÓN', 'ar': 'تسجيل الخروج'},

    # ── BACKEND API MESSAGES (returned from server, translated by lang) ──
    'api_plan_not_found':    {'en': 'Plan not found',           'es': 'Plan no encontrado', 'ar': 'الخطة غير موجودة'},
    'api_plan_unavailable':  {'en': 'This plan is not available', 'es': 'Este plan no está disponible', 'ar': 'هذه الخطة غير متاحة'},
    'api_user_not_found':    {'en': 'User not found',           'es': 'Usuario no encontrado', 'ar': 'المستخدم غير موجود'},
    'api_free_plan_once':    {
        'en': 'The {name} plan is free and can only be activated once per account.',
        'es': 'El plan {name} es gratuito y solo puede activarse una vez por cuenta.', 'ar': 'خطة {name} مجانية ويمكن تفعيلها مرة واحدة فقط لكل حساب.'},
    'api_plan_active_until': {
        'en': 'You already have this plan active. You can renew it on {date}.',
        'es': 'Ya tienes este plan activo. Podrás renovarlo el {date}.', 'ar': 'لديك هذه الخطة نشطة بالفعل. يمكنك تجديدها في {date}.'},
    'api_insufficient_funds':{
        'en': 'Insufficient balance. You need {amount} TON',
        'es': 'Saldo insuficiente. Necesitas {amount} TON', 'ar': 'الرصيد غير كافٍ. تحتاج {amount} TON'},
    'api_plan_activated_free':{
        'en': 'Plan {name} activated for free! Start earning TON.',
        'es': '¡Plan {name} activado gratis! Empieza a ganar TON.', 'ar': 'تم تفعيل خطة {name} مجانًا! ابدأ ربح TON.'},
    'api_plan_activated_paid':{
        'en': 'Plan {name} activated for {price} TON! Start earning TON.',
        'es': '¡Plan {name} activado por {price} TON! Empieza a ganar TON.', 'ar': 'تم تفعيل خطة {name} مقابل {price} TON! ابدأ ربح TON.'},
    'api_no_wallet':         {'en': 'Connect your TON wallet first', 'es': 'Conecta tu wallet TON primero', 'ar': 'اربط محفظة TON الخاصة بك أولاً'},
    'api_no_wallet_profile': {'en': 'Link your TON wallet from your Profile first.', 'es': 'Primero vincula tu wallet TON desde tu Perfil.', 'ar': 'اربط محفظة TON من ملفك الشخصي أولاً.'},
    'api_wd_disabled':       {'en': 'TON withdrawals temporarily disabled', 'es': 'Retiros TON temporalmente deshabilitados', 'ar': 'سحوبات TON معطّلة مؤقتًا'},
    'api_dep_disabled':      {'en': 'TON deposits disabled',        'es': 'Depósitos TON deshabilitados', 'ar': 'إيداعات TON معطّلة'},
    'api_bot_addr_missing':  {'en': 'Bot address not configured. Contact admin.', 'es': 'Dirección del bot no configurada. Contacta al admin.', 'ar': 'عنوان البوت غير مُعد. تواصل مع الإدارة.'},
    'api_min_withdrawal':    {
        'en': 'Minimum withdrawal: {amount} TON',
        'es': 'Mínimo de retiro: {amount} TON', 'ar': 'الحد الأدنى للسحب: {amount} TON'},
    'api_insuf_balance':     {'en': 'Insufficient balance',        'es': 'Saldo insuficiente', 'ar': 'الرصيد غير كافٍ'},
    'api_no_machines':       {'en': 'No active mining machines',   'es': 'No tienes máquinas activas', 'ar': 'لا توجد أجهزة تعدين نشطة'},
    'api_claimed_rewards':   {'en': 'Claimed {claimed} TON!',      'es': '¡{claimed} TON reclamados!', 'ar': 'تم استلام {claimed} TON!'},
    'api_no_rewards':        {'en': 'No rewards to claim',         'es': 'No hay recompensas para reclamar', 'ar': 'لا توجد مكافآت للاستلام'},
    'api_claim_cooldown':    {
        'en': 'You can claim again in {wait}',
        'es': 'Puedes reclamar de nuevo en {wait}', 'ar': 'يمكنك الاستلام مرة أخرى بعد {wait}'},
}


def get_t(lang='en'):
    """
    Return a SimpleNamespace-like dict that lets templates do:
        {{ t.key }}
    Falls back to English if key or lang is missing.
    """
    class T:
        def __getattr__(self, key):
            entry = TRANSLATIONS.get(key)
            if entry is None:
                return key  # return raw key as fallback
            return entry.get(lang) or entry.get('en') or key

        def __getitem__(self, key):
            return self.__getattr__(key)

    return T()


# Idiomas que se leen de DERECHA A IZQUIERDA
RTL_LANGS = ['ar']


def is_rtl(lang):
    """True si el idioma se escribe de derecha a izquierda."""
    return lang in RTL_LANGS


def get_supported_langs():
    return ['en', 'es', 'ar']
