import 'package:flutter/material.dart';

import 'core/app_identity.dart';
import 'core/theme/app_theme.dart';
import 'data/app_database.dart';
import 'domain/allocation_engine.dart';
import 'features/home/dashboard_screen.dart';
import 'features/insights/insights_screen.dart';
import 'features/plan/plan_screen.dart';
import 'features/setup/setup_wizard_screen.dart';
import 'features/settings/settings_screen.dart';
import 'features/transactions/transactions_screen.dart';
import 'state/app_controller.dart';

class PrepPersonalApp extends StatelessWidget {
  const PrepPersonalApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: appDisplayName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      home: const AppBootstrap(),
    );
  }
}

class AppBootstrap extends StatefulWidget {
  const AppBootstrap({super.key});

  @override
  State<AppBootstrap> createState() => _AppBootstrapState();
}

class _AppBootstrapState extends State<AppBootstrap> {
  static const _minimumSplashDuration = Duration(milliseconds: 4500);

  late final Future<AppController> _bootstrap;

  @override
  void initState() {
    super.initState();
    _bootstrap = _initialize();
  }

  Future<AppController> _initialize() async {
    final database = AppDatabase();
    final controller = AppController(
      database: database,
      engine: const IncomeAllocationEngine(),
    );

    await Future.wait([
      () async {
        await database.initialize();
        await controller.load();
      }(),
      Future<void>.delayed(_minimumSplashDuration),
    ]);

    return controller;
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<AppController>(
      future: _bootstrap,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const _LoadingScreen();
        }

        if (snapshot.hasError || !snapshot.hasData) {
          return Scaffold(
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'No se pudo iniciar la base local de $appDisplayName.',
                  style: Theme.of(context).textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
              ),
            ),
          );
        }

        return AnimatedBuilder(
          animation: snapshot.data!,
          builder: (context, _) {
            return Theme(
              data: AppTheme.themeForPalette(snapshot.data!.selectedPaletteId),
              child: AppShell(controller: snapshot.data!),
            );
          },
        );
      },
    );
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key, required this.controller});

  final AppController controller;

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        if (!widget.controller.setupComplete) {
          return SetupWizardScreen(controller: widget.controller);
        }

        final screens = [
          DashboardScreen(controller: widget.controller),
          TransactionsScreen(controller: widget.controller),
          PlanScreen(controller: widget.controller),
          InsightsScreen(controller: widget.controller),
          SettingsScreen(controller: widget.controller),
        ];

        return Scaffold(
          body: SafeArea(
            child: IndexedStack(index: _currentIndex, children: screens),
          ),
          bottomNavigationBar: NavigationBar(
            selectedIndex: _currentIndex,
            onDestinationSelected: (index) {
              setState(() {
                _currentIndex = index;
              });
            },
            destinations: const [
              NavigationDestination(icon: Icon(Icons.home_outlined), label: 'Inicio'),
              NavigationDestination(
                icon: Icon(Icons.sync_alt_outlined),
                label: 'Transacciones',
              ),
              NavigationDestination(
                icon: Icon(Icons.event_note_outlined),
                label: 'Plan',
              ),
              NavigationDestination(
                icon: Icon(Icons.insights_outlined),
                label: 'Insights',
              ),
              NavigationDestination(
                icon: Icon(Icons.tune_outlined),
                label: 'Ajustes',
              ),
            ],
          ),
        );
      },
    );
  }
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.ivory,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const _NeonSplashMark(),
              const SizedBox(height: 18),
              Text(
                appDisplayName,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      letterSpacing: -0.6,
                      color: AppColors.petrol,
                    ),
              ),
              const SizedBox(height: 8),
              Text(appTagline, style: Theme.of(context).textTheme.bodyLarge, textAlign: TextAlign.center),
              const SizedBox(height: 22),
              const SizedBox(width: 34, height: 34, child: CircularProgressIndicator()),
            ],
          ),
        ),
      ),
    );
  }
}

class _NeonSplashMark extends StatefulWidget {
  const _NeonSplashMark();

  @override
  State<_NeonSplashMark> createState() => _NeonSplashMarkState();
}

class _NeonSplashMarkState extends State<_NeonSplashMark> with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 4800),
    )..repeat();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final assemble = Curves.easeOutExpo.transform(
          Interval(0.0, 0.38).transform(_controller.value.clamp(0.0, 1.0)),
        );
        final settle = Curves.easeInOut.transform(
          Interval(0.38, 0.55).transform(_controller.value.clamp(0.0, 1.0)),
        );
        final floatPhase = Interval(0.55, 1.0).transform(_controller.value.clamp(0.0, 1.0));
        final floatOffset = 8 * (0.5 - (0.5 - floatPhase).abs()) * 2;
        final shimmer = Curves.easeInOut.transform(
          Interval(0.18, 0.62).transform(_controller.value.clamp(0.0, 1.0)),
        );
        final shellOffset = (1 - assemble) * 36;
        final coreOffset = (1 - assemble) * 26;
        final badgeOffset = (1 - assemble) * 18;
        final composedScale = 0.88 + (assemble * 0.12) - (settle * 0.03);

        return Transform.translate(
          offset: Offset(0, -floatOffset),
          child: Transform.scale(
            scale: composedScale,
            child: SizedBox(
              width: 190,
              height: 204,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Positioned(
                    top: 18 + shellOffset,
                    child: Container(
                      width: 168,
                      height: 168,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(42),
                        gradient: LinearGradient(
                          colors: [AppColors.petrol, AppColors.emerald],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.petrol.withValues(alpha: 0.18 + (floatPhase * 0.06)),
                            blurRadius: 30,
                            offset: Offset(0, 20 + floatOffset),
                          ),
                        ],
                      ),
                    ),
                  ),
                  Positioned(
                    top: 31 + coreOffset,
                    child: Container(
                      width: 128,
                      height: 128,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(32),
                        color: AppColors.paper.withValues(alpha: 0.08),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
                      ),
                    ),
                  ),
                  Positioned(
                    top: 24 + badgeOffset,
                    child: Opacity(
                      opacity: 0.2 + (shimmer * 0.8),
                      child: Container(
                        width: 142,
                        height: 142,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(38),
                          gradient: SweepGradient(
                            transform: GradientRotation((0.35 + shimmer) * 6.28318),
                            colors: [
                              Colors.transparent,
                              AppColors.gold.withValues(alpha: 0.18),
                              Colors.white.withValues(alpha: 0.94),
                              AppColors.gold.withValues(alpha: 0.22),
                              Colors.transparent,
                            ],
                            stops: const [0.0, 0.2, 0.38, 0.56, 1.0],
                          ),
                        ),
                      ),
                    ),
                  ),
                  Positioned(
                    top: 38,
                    child: Transform.translate(
                      offset: Offset(0, -badgeOffset),
                      child: Container(
                        width: 114,
                        height: 114,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(28),
                          color: AppColors.ivory,
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'GL',
                              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                                    fontSize: 34,
                                    color: AppColors.petrol,
                                  ),
                            ),
                            Text(
                              'Ledger',
                              style: Theme.of(context).textTheme.labelLarge?.copyWith(color: AppColors.gold),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}