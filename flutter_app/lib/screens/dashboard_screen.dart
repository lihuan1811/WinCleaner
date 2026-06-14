import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Expanded(flex: 2, child: _StorageCard()),
              const SizedBox(width: 32),
              Expanded(child: _HealthCard()),
            ],
          ),
          const SizedBox(height: 34),
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('高级工具箱', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 4),
                  const Text(
                    '深层优化您的电脑性能',
                    style: TextStyle(color: AppColors.muted),
                  ),
                ],
              ),
              const Spacer(),
              TextButton.icon(
                onPressed: () {},
                label: const Text('查看全部工具'),
                icon: const Icon(Icons.chevron_right),
                iconAlignment: IconAlignment.end,
              ),
            ],
          ),
          const SizedBox(height: 24),
          const Row(
            children: [
              Expanded(
                child: _ToolCard(
                  icon: Icons.block_outlined,
                  title: '广告清理',
                  subtitle: '强力拦截网页及弹窗广告',
                ),
              ),
              SizedBox(width: 24),
              Expanded(
                child: _ToolCard(
                  icon: Icons.copy_outlined,
                  title: '重复文件',
                  subtitle: '智能识别并清理多余副本',
                ),
              ),
              SizedBox(width: 24),
              Expanded(
                child: _ToolCard(
                  icon: Icons.sd_storage_outlined,
                  title: '超大文件',
                  subtitle: '快速查找GB级别的冗余文件',
                ),
              ),
              SizedBox(width: 24),
              Expanded(
                child: _ToolCard(
                  icon: Icons.grid_view_outlined,
                  title: '碎片整理',
                  subtitle: '重新排列磁盘数据提升读写',
                ),
              ),
            ],
          ),
          const SizedBox(height: 32),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Expanded(flex: 2, child: _TrendCard()),
              const SizedBox(width: 32),
              Expanded(child: _ActivityCard()),
            ],
          ),
        ],
      ),
    );
  }
}

class _StorageCard extends StatelessWidget {
  const _StorageCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '系统存储监控',
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    '正在实时分析驱动器 C: 的健康状况',
                    style: TextStyle(color: AppColors.muted),
                  ),
                  const SizedBox(height: 34),
                  const Row(
                    children: [
                      _Metric(label: '已用空间', value: '384.2 GB'),
                      SizedBox(width: 30),
                      SizedBox(
                        height: 52,
                        child: VerticalDivider(color: AppColors.border),
                      ),
                      SizedBox(width: 30),
                      _Metric(label: '剩余空间', value: '127.8 GB', dark: true),
                    ],
                  ),
                  const SizedBox(height: 28),
                  Row(
                    children: [
                      FilledButton.icon(
                        style: FilledButton.styleFrom(
                          fixedSize: const Size(220, 62),
                          backgroundColor: AppColors.primaryDark,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        onPressed: () {},
                        icon: const Icon(Icons.search),
                        label: const Text(
                          '一键开始扫描',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                      const SizedBox(width: 18),
                      OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          fixedSize: const Size(150, 62),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(10),
                          ),
                        ),
                        onPressed: () {},
                        child: const Text(
                          '详细报告',
                          style: TextStyle(fontWeight: FontWeight.w800),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(width: 30),
            const SizedBox(
              width: 230,
              height: 230,
              child: _PercentRing(percent: .75),
            ),
          ],
        ),
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, this.dark = false});

  final String label;
  final String value;
  final bool dark;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: AppColors.muted)),
        const SizedBox(height: 8),
        Text(
          value,
          style: TextStyle(
            fontSize: 30,
            fontWeight: FontWeight.w900,
            color: dark ? AppColors.text : AppColors.primaryDark,
          ),
        ),
      ],
    );
  }
}

class _PercentRing extends StatelessWidget {
  const _PercentRing({required this.percent});

  final double percent;

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.center,
      children: [
        SizedBox(
          width: 210,
          height: 210,
          child: CircularProgressIndicator(
            value: percent,
            strokeWidth: 22,
            backgroundColor: const Color(0xFFE5EBF4),
            color: AppColors.primary,
            strokeCap: StrokeCap.butt,
          ),
        ),
        const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              '75%',
              style: TextStyle(
                fontSize: 52,
                fontWeight: FontWeight.w900,
                color: AppColors.primaryDark,
              ),
            ),
            Text(
              '占用率',
              style: TextStyle(
                color: AppColors.muted,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _HealthCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('系统健康状态', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 28),
            const Row(
              children: [
                CircleAvatar(
                  radius: 42,
                  backgroundColor: Color(0xFFE6ECF5),
                  child: Icon(
                    Icons.shield_outlined,
                    color: AppColors.primary,
                    size: 40,
                  ),
                ),
                SizedBox(width: 22),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '良好',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        color: AppColors.primaryDark,
                      ),
                    ),
                    Text(
                      '上次检查: 2小时前',
                      style: TextStyle(color: AppColors.muted),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 36),
            const _HealthLine(label: '启动项', value: '12 个高能耗', percent: .45),
            const SizedBox(height: 26),
            const _HealthLine(
              label: '内存占用',
              value: '3.2 GB / 16 GB',
              percent: .2,
            ),
          ],
        ),
      ),
    );
  }
}

class _HealthLine extends StatelessWidget {
  const _HealthLine({
    required this.label,
    required this.value,
    required this.percent,
  });

  final String label;
  final String value;
  final double percent;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            Text(label, style: const TextStyle(color: AppColors.muted)),
            const Spacer(),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w800)),
          ],
        ),
        const SizedBox(height: 10),
        LinearProgressIndicator(
          value: percent,
          minHeight: 6,
          borderRadius: BorderRadius.circular(4),
        ),
      ],
    );
  }
}

class _ToolCard extends StatelessWidget {
  const _ToolCard({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        height: 170,
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: AppColors.paleBlue,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: AppColors.text),
              ),
              const Spacer(),
              Text(title, style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 6),
              Text(
                subtitle,
                style: const TextStyle(color: AppColors.muted, fontSize: 13),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TrendCard extends StatelessWidget {
  const _TrendCard();

  @override
  Widget build(BuildContext context) {
    final values = [12, 20, 11, 28, 17, 23, 32];
    final labels = ['周一', '周二', '周三', '周四', '周五', '周六', '今天'];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('最近清理趋势', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 34),
            SizedBox(
              height: 230,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (var i = 0; i < values.length; i++)
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 5),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            Expanded(
                              child: Align(
                                alignment: Alignment.bottomCenter,
                                child: FractionallySizedBox(
                                  heightFactor: values[i] / 36,
                                  child: Container(
                                    decoration: BoxDecoration(
                                      color: i == values.length - 1
                                          ? AppColors.primaryDark
                                          : const Color(0xFFD8E4FF),
                                      borderRadius: const BorderRadius.vertical(
                                        top: Radius.circular(3),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: 14),
                            Text(
                              labels[i],
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: i == values.length - 1
                                    ? FontWeight.w800
                                    : FontWeight.w500,
                                color: AppColors.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ActivityCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('实时活动日志', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 26),
            const _Activity(
              icon: Icons.done_all,
              color: Color(0xFFD8FBE4),
              title: '成功清理 12.4 GB',
              subtitle: '35 分钟前 · 临时文件',
            ),
            const _Activity(
              icon: Icons.sync,
              color: Color(0xFFDDEBFF),
              title: '数据库更新完成',
              subtitle: '2 小时前 · 版本 v4.5.2',
            ),
            const _Activity(
              icon: Icons.warning_amber,
              color: Color(0xFFFFF1C7),
              title: '发现 5 个安全威胁',
              subtitle: '昨天 18:42 · 深度扫描',
            ),
          ],
        ),
      ),
    );
  }
}

class _Activity extends StatelessWidget {
  const _Activity({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 22),
      child: Row(
        children: [
          CircleAvatar(
            radius: 21,
            backgroundColor: color,
            child: Icon(icon, color: AppColors.primary, size: 22),
          ),
          const SizedBox(width: 18),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.w800,
                  color: AppColors.text,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                subtitle,
                style: const TextStyle(color: AppColors.muted, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
