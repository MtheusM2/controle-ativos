import {
  Package,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Search,
  Filter,
  Download,
  Plus,
  Edit,
  Trash2,
  Eye
} from 'lucide-react';

interface Asset {
  id: string;
  name: string;
  category: string;
  serialNumber: string;
  status: 'active' | 'maintenance' | 'inactive';
  location: string;
  purchaseDate: string;
  value: string;
}

const mockAssets: Asset[] = [
  {
    id: '1',
    name: 'Monitor Dell UltraSharp 27"',
    category: 'Informática',
    serialNumber: 'DELL2023001',
    status: 'active',
    location: 'Sala 301',
    purchaseDate: '2023-01-15',
    value: 'R$ 2.500,00'
  },
  {
    id: '2',
    name: 'Notebook HP EliteBook',
    category: 'Informática',
    serialNumber: 'HP2023045',
    status: 'active',
    location: 'Sala 205',
    purchaseDate: '2023-03-20',
    value: 'R$ 4.800,00'
  },
  {
    id: '3',
    name: 'Cadeira Ergonômica',
    category: 'Mobiliário',
    serialNumber: 'MOB2023012',
    status: 'maintenance',
    location: 'Sala 102',
    purchaseDate: '2023-02-10',
    value: 'R$ 1.200,00'
  },
  {
    id: '4',
    name: 'Projetor Epson',
    category: 'Audiovisual',
    serialNumber: 'EPSON2023008',
    status: 'active',
    location: 'Auditório',
    purchaseDate: '2023-04-05',
    value: 'R$ 3.500,00'
  },
  {
    id: '5',
    name: 'Impressora HP LaserJet',
    category: 'Informática',
    serialNumber: 'HP2023087',
    status: 'inactive',
    location: 'Almoxarifado',
    purchaseDate: '2022-11-30',
    value: 'R$ 1.800,00'
  },
];

interface DashboardProps {
  onEditAsset: (assetId: string) => void;
}

export function Dashboard({ onEditAsset }: DashboardProps) {
  const stats = [
    {
      title: 'Total de Ativos',
      value: '248',
      icon: Package,
      color: 'bg-blue-50 text-blue-600',
      iconBg: 'bg-blue-100'
    },
    {
      title: 'Ativos Ativos',
      value: '212',
      icon: CheckCircle2,
      color: 'bg-green-50 text-green-600',
      iconBg: 'bg-green-100'
    },
    {
      title: 'Em Manutenção',
      value: '18',
      icon: AlertCircle,
      color: 'bg-yellow-50 text-yellow-600',
      iconBg: 'bg-yellow-100'
    },
    {
      title: 'Valor Total',
      value: 'R$ 1.2M',
      icon: TrendingUp,
      color: 'bg-primary/10 text-primary',
      iconBg: 'bg-primary/20'
    },
  ];

  const getStatusBadge = (status: Asset['status']) => {
    const styles = {
      active: 'bg-green-100 text-green-800 border-green-200',
      maintenance: 'bg-yellow-100 text-yellow-800 border-yellow-200',
      inactive: 'bg-gray-100 text-gray-800 border-gray-200'
    };

    const labels = {
      active: 'Ativo',
      maintenance: 'Manutenção',
      inactive: 'Inativo'
    };

    return (
      <span className={`px-3 py-1 rounded-full text-xs border ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  return (
    <div>
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.title} className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-gray-500 mb-1">{stat.title}</p>
                  <p className="text-2xl text-gray-900">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.iconBg}`}>
                  <Icon className={`w-6 h-6 ${stat.color.split(' ')[1]}`} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Filters and Actions */}
      <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm mb-6">
        <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
          <div className="flex-1 w-full lg:w-auto">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar ativos..."
                className="w-full pl-11 pr-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3 w-full lg:w-auto">
            <button className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
              <Filter className="w-4 h-4" />
              <span>Filtros</span>
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
              <Download className="w-4 h-4" />
              <span>Exportar</span>
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 bg-primary text-white rounded-lg hover:bg-red-700 transition-colors">
              <Plus className="w-4 h-4" />
              <span>Novo Ativo</span>
            </button>
          </div>
        </div>
      </div>

      {/* Assets Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Ativo
                </th>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Categoria
                </th>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Nº Série
                </th>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Localização
                </th>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Valor
                </th>
                <th className="px-6 py-4 text-left text-xs text-gray-600 uppercase tracking-wider">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {mockAssets.map((asset) => (
                <tr key={asset.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">{asset.name}</div>
                    <div className="text-xs text-gray-500">Comprado em {new Date(asset.purchaseDate).toLocaleDateString('pt-BR')}</div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {asset.category}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600 font-mono">
                    {asset.serialNumber}
                  </td>
                  <td className="px-6 py-4">
                    {getStatusBadge(asset.status)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {asset.location}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {asset.value}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors" title="Visualizar">
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => onEditAsset(asset.id)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                        title="Editar"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                      <button className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="Excluir">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Mostrando <span className="text-gray-900">1</span> a <span className="text-gray-900">5</span> de <span className="text-gray-900">248</span> ativos
          </p>
          <div className="flex gap-2">
            <button className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors text-sm">
              Anterior
            </button>
            <button className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-red-700 transition-colors text-sm">
              Próxima
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
